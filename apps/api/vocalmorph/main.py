import asyncio, concurrent.futures, multiprocessing, hashlib, io, json, os, shutil, tempfile, threading, uuid
from contextlib import asynccontextmanager
from pathlib import Path
import numpy as np
import soundfile as sf
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from .engine import parameters, cache_key, resample, transform_audio, DEFAULTS
from .models import BUILTINS, validate, install_zip, ID, digest
ROOT=Path(os.environ.get("VOCALMORPH_DATA",Path.home()/".vocalmorph"))
for name in ("audio","models","cache","presets","jobs"): (ROOT/name).mkdir(parents=True,exist_ok=True)
JOBS={};LOCK=threading.RLock();POOL=None

def run_job(audio,output,p,model):
 x,sr=sf.read(audio,dtype="float32");y=transform_audio(x,sr,p,model)
 temp=output+".tmp.wav";sf.write(temp,y,sr,subtype="PCM_24");os.replace(temp,output)
 return output
@asynccontextmanager
async def lifespan(app):
 global POOL
 POOL=concurrent.futures.ProcessPoolExecutor(max_workers=1,mp_context=multiprocessing.get_context("spawn"))
 yield
 POOL.shutdown(wait=True,cancel_futures=True)
app=FastAPI(title="VocalMorph",version="0.1.0",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:3000","http://127.0.0.1:3000"],allow_methods=["GET","POST","DELETE"],allow_headers=["*"])

def model_list():
 models=[dict(m) for m in BUILTINS]
 for p in (ROOT/"models").glob("*/manifest.json"):
  try:models.append(validate(p.parent,verify=False))
  except Exception:continue
 return models

def locate_model(key,version):
 if any(m["id"]==key and m["version"]==version for m in BUILTINS):return None
 if not ID.fullmatch(key):raise HTTPException(422,"Invalid model ID")
 p=ROOT/"models"/(key+"@"+version)
 if not p.is_dir():raise HTTPException(404,"Model version not installed")
 return p

@app.get("/api/health")
def health():return dict(status="ready",version="0.1.0",neural_models=sum(m["architecture"]!="dsp" for m in model_list()))
@app.get("/api/models")
def models():return model_list()
@app.get("/api/models/catalog")
def catalog():return [] # No authorized voice catalog is bundled; install your own packages.
@app.post("/api/models/import")
async def import_model(file:UploadFile=File(...)):
 temp=ROOT/(uuid.uuid4().hex+".zip")
 try:
  size=0
  with temp.open("wb") as out:
   while data:=await file.read(1024*1024):
    size+=len(data)
    if size>2*1024**3:raise HTTPException(413,"Package exceeds 2 GB")
    out.write(data)
  return await asyncio.to_thread(install_zip,temp,ROOT/"models")
 except (ValueError,KeyError,OSError) as e:raise HTTPException(422,str(e))
 finally:temp.unlink(missing_ok=True)
@app.delete("/api/models/{key}/{version}")
def delete_model(key:str,version:str):
 path=locate_model(key,version)
 if path is None:raise HTTPException(403,"Factory styles cannot be deleted")
 with LOCK:
  if any(j.get("model")==key and j["status"] in ("queued","running") for j in JOBS.values()):raise HTTPException(409,"Model is in use")
  shutil.rmtree(path)
 return {"deleted":True}
@app.get("/api/models/{key}/{version}/preview")
def preview(key:str,version:str):
 path=locate_model(key,version)
 if path is None:raise HTTPException(404,"No voice demo: this is a DSP style")
 m=validate(path,verify=False);name=m.get("preview")
 if not name or name not in m["files"] or not name.endswith(".wav"):raise HTTPException(404,"No licensed preview included")
 return FileResponse(path/name,media_type="audio/wav")
@app.post("/api/upload")
async def upload(file:UploadFile=File(...),normalize:bool=Form(False)):
 data=await file.read(64*1024*1024+1)
 if len(data)>64*1024*1024:raise HTTPException(413,"Maximum upload is 64 MB")
 def decode():
  try:
   with sf.SoundFile(io.BytesIO(data)) as f:
    if f.frames>f.samplerate*300 or f.channels>8 or not 8000<=f.samplerate<=192000:raise ValueError("Use audio under 5 minutes, 8 channels and 192 kHz")
    sr=f.samplerate;x=f.read(dtype="float32",always_2d=True).mean(axis=1)
  except Exception as e:raise ValueError("Use a valid WAV, FLAC or OGG recording. "+str(e))
  if len(x)<sr*.1 or not np.isfinite(x).all():raise ValueError("Audio must contain at least 0.1 seconds of finite samples")
  x=resample(x,sr,48000);x-=x.mean();peak=float(np.max(np.abs(x)))
  if peak<1e-6:raise ValueError("Recording is silent")
  if normalize:x=x/peak*.89125
  key=hashlib.sha256(x.astype("<f4").tobytes()).hexdigest();sf.write(ROOT/"audio"/(key+".wav"),x,48000,subtype="FLOAT")
  return dict(id=key,duration=len(x)/48000,sample_rate=48000,channels=1,peak=peak,url="/api/audio/"+key)
 try:return await asyncio.to_thread(decode)
 except ValueError as e:raise HTTPException(422,str(e))

class Transform(BaseModel):
 source:str=Field(pattern=r"^[a-f0-9]{64}$")
 model:str="studio-clean"
 version:str=Field(default="1.0.0",pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
 parameters:dict[str,float]=Field(default_factory=dict)
@app.post("/api/transform")
def transform(req:Transform):
 try:p=parameters(req.parameters)
 except ValueError as e:raise HTTPException(422,str(e))
 source=ROOT/"audio"/(req.source+".wav")
 if not source.exists():raise HTTPException(404,"Source audio not found")
 model=locate_model(req.model,req.version)
 try:identity=validate(model) if model else next(m for m in BUILTINS if m["id"]==req.model)
 except ValueError as e:raise HTTPException(422,str(e))
 key=cache_key(req.source,identity,p);output=ROOT/"cache"/(key+".wav")
 with LOCK:
  if output.exists():return dict(id=key,status="complete",cached=True,url="/api/audio/"+key)
  if key in JOBS and JOBS[key]["status"] in ("queued","running"):return JOBS[key]
  if sum(j["status"] in ("queued","running") for j in JOBS.values())>=8:raise HTTPException(429,"Processing queue is full")
  job=dict(id=key,status="queued",progress=0,model=req.model,cached=False);JOBS[key]=job
  if POOL is None:raise HTTPException(503,"Worker unavailable")
  future=POOL.submit(run_job,str(source),str(output),p,str(model) if model else None)
  job["status"]="running";job["progress"]=.1
  def done(f):
   with LOCK:
    try:f.result();job.update(status="complete",progress=1,url="/api/audio/"+key)
    except Exception as e:job.update(status="failed",error=str(e),progress=0)
  future.add_done_callback(done)
 return job
@app.get("/api/jobs/{key}")
def job(key:str):
 if key not in JOBS:raise HTTPException(404,"Job not found")
 return JOBS[key]
@app.get("/api/audio/{key}")
def audio(key:str):
 if len(key)!=64 or any(c not in "0123456789abcdef" for c in key):raise HTTPException(404)
 for folder in ("audio","cache"):
  p=ROOT/folder/(key+".wav")
  if p.is_file():return FileResponse(p,media_type="audio/wav",filename="VocalMorph-"+key[:8]+".wav")
 raise HTTPException(404,"Audio not found")
@app.get("/api/cache")
def cache():
 files=list((ROOT/"cache").glob("*.wav"));return dict(entries=len(files),bytes=sum(p.stat().st_size for p in files))
@app.delete("/api/cache")
def clear_cache():
 with LOCK:
  if any(j["status"] in ("queued","running") for j in JOBS.values()):raise HTTPException(409,"Wait for active jobs before clearing cache")
  for p in (ROOT/"cache").glob("*.wav"):p.unlink()
 return dict(cleared=True)
class Preset(BaseModel):
 name:str=Field(min_length=1,max_length=80)
 category:str="Custom"
 model:str="studio-clean"
 version:str="1.0.0"
 parameters:dict[str,float]
@app.get("/api/presets")
def presets():
 factory=[]
 for category,change in [("Pop",{"brightness":.25,"air":.2}),("Rock",{"aggression":.35,"body":.3}),("Metal",{"aggression":.75,"dynamics":.55}),("Clean",{}),("Character",{"pitch":-5,"formant":-3}),("Creative",{"pitch":7,"air":.7})]:
  factory.append(dict(id="factory-"+category.lower(),name=category+" / Init",category=category,model="studio-clean",version="1.0.0",parameters={**DEFAULTS,**change},factory=True))
 for f in (ROOT/"presets").glob("*.json"):
  try:factory.append(json.loads(f.read_text()))
  except (ValueError,OSError):continue
 return factory
@app.post("/api/presets")
def save_preset(preset:Preset):
 try:p=parameters(preset.parameters)
 except ValueError as e:raise HTTPException(422,str(e))
 key=uuid.uuid4().hex;result={**preset.model_dump(),"parameters":p,"id":key,"factory":False};(ROOT/"presets"/(key+".json")).write_text(json.dumps(result));return result

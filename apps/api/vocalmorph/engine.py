"""Shared inference implementation for the web worker and bundled VST worker."""
import ctypes, hashlib, json, math, os, sys
from pathlib import Path
import numpy as np
from scipy.signal import resample_poly
from .models import validate
IDS=["pitch","formant","expression","brightness","body","air","aggression","smoothness","dynamics","breath","consonants","sibilance","mix","input","output","autotune","tuneSpeed"]
DEFAULTS=dict(zip(IDS,[0,0,.5,0,0,0,0,0,0,0,.5,0,1,0,0,0,.5]))
LIMITS=list(zip([-24,-12,0,-1,-1,0,0,0,0,0,0,0,0,-24,-24,0,0],[24,12,1,1,1,1,1,1,1,1,1,1,1,24,24,1,1]))
PIPELINE_VERSION="vm-0.1.0-rvc-81eed5e8-dsp2"
def parameters(values):
 if set(values)-set(IDS):raise ValueError("Unknown parameter")
 p={**DEFAULTS,**values}
 for key,(lo,hi) in zip(IDS,LIMITS):
  v=p[key]
  if not isinstance(v,(float,int)) or not math.isfinite(v) or not lo<=v<=hi:raise ValueError("Out-of-range parameter: "+key)
 return p

def cache_key(source,model,p):
 payload=dict(pipeline=PIPELINE_VERSION,source=source,model=model,parameters=parameters(p))
 return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def resample(x,old,new):
 if old==new:return np.asarray(x,dtype=np.float32)
 g=math.gcd(int(old),int(new));return resample_poly(x,int(new)//g,int(old)//g).astype(np.float32)

def dsp(x,sr,p):
 candidates=[os.environ.get("VOCALMORPH_DSP","")]
 base=Path(__file__).resolve().parents[3]
 candidates += [str(base/"build/core/libvocalmorph_dsp.so"),str(base/"build/core/Release/vocalmorph_dsp.dll"),str(Path(sys.executable).parent/"vocalmorph_dsp.dll")]
 path=next((v for v in candidates if v and Path(v).is_file()),None)
 if not path:raise RuntimeError("Build VocalMorphCore first or set VOCALMORPH_DSP to its shared library")
 lib=ctypes.CDLL(path);fn=lib.vm_process
 fn.argtypes=[ctypes.POINTER(ctypes.c_float),ctypes.c_size_t,ctypes.c_double,ctypes.POINTER(ctypes.c_float),ctypes.c_size_t];fn.restype=ctypes.c_int
 audio=np.ascontiguousarray(x,dtype=np.float32).copy();pv=np.array([parameters(p)[k] for k in IDS],dtype=np.float32)
 rc=fn(audio.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),len(audio),sr,pv.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),len(pv))
 if rc:raise RuntimeError("Native DSP rejected input")
 return audio

def resolve_model_source(source):
 p=Path(source)
 if p.is_file():
  if p.suffix.lower()==".pth":return p,p.parent,None
  if p.name.lower()=="manifest.json":return p.parent/"model.pth",p.parent,p
  raise ValueError("Choose an RVC .pth file")
 if not p.is_dir():raise ValueError("Model path does not exist")
 manifest=p/"manifest.json"
 if manifest.is_file():return p/"model.pth",p,manifest
 checkpoints=sorted(p.glob("*.pth"))
 if len(checkpoints)==1:return checkpoints[0],p,None
 if not checkpoints:raise ValueError("No RVC .pth model found")
 raise ValueError("Multiple .pth files found; choose the model file directly")

def resolve_support_assets(model_dir):
 candidates=[]
 env=os.environ.get("VOCALMORPH_ASSETS","")
 if env:candidates.append(Path(env))
 model_dir=Path(model_dir)
 candidates += [model_dir,model_dir/"assets",Path(__file__).resolve().parents[2]/"assets"]
 for root in candidates:
  layouts=((root/"rmvpe"/"rmvpe.pt",root/"hubert_base"),(root/"rmvpe.pt",root/"hubert"))
  for rmvpe,hubert in layouts:
   weight=hubert/"model.safetensors"
   if not weight.is_file():weight=hubert/"pytorch_model.bin"
   if rmvpe.is_file() and (hubert/"config.json").is_file() and (hubert/"preprocessor_config.json").is_file() and weight.is_file():
    return rmvpe,hubert
 raise ValueError("RVC model detected, but the RMVPE/HuBERT support bundle is missing. Reinstall the full VocalMorph package; expected Resources/assets/rmvpe/rmvpe.pt and Resources/assets/hubert_base/.")

class RvcEngine:
 def __init__(self,root):
  self.model_path,self.root,manifest_path=resolve_model_source(root)
  self.manifest=validate(self.root) if manifest_path is not None else None
  self.rmvpe_path,self.hubert_dir=resolve_support_assets(self.root)
  os.environ["TORCH_FORCE_WEIGHTS_ONLY_LOAD"]="1"
  os.environ["HF_HUB_OFFLINE"]="1"
  upstream=Path(os.environ.get("VOCALMORPH_RVC",Path(__file__).resolve().parents[3]/"third_party/rvc"))
  if not (upstream/"infer/module/models.py").is_file():raise RuntimeError("Pinned RVC dependency is missing; run tools/bootstrap.py")
  sys.path.insert(0,str(upstream))
  import torch
  from infer.module.models import SynthesizerTrnMs256NSFsid,SynthesizerTrnMs768NSFsid
  from infer.rmvpe import RMVPE
  from infer.hubert import HubertModelWithFinalProj
  from transformers import AutoFeatureExtractor
  torch.set_num_threads(max(1,min(4,(os.cpu_count() or 2)//2)))
  self.torch=torch
  c=torch.load(self.model_path,map_location="cpu",weights_only=True)
  if not isinstance(c,dict) or not isinstance(c.get("weight"),dict) or len(c.get("config",[]))!=18:raise ValueError("Not a supported RVC inference checkpoint")
  self.version=c.get("version","v1")
  if self.version not in ("v1","v2"):raise ValueError("Only RVC v1/v2 checkpoints are supported")
  if c.get("f0",1)!=1:raise ValueError("RVC checkpoint must include F0 support")
  if self.manifest is not None and "rvc-"+self.version!=self.manifest["architecture"]:raise ValueError("Checkpoint architecture differs from manifest")
  cfg=list(c["config"])
  if any(not isinstance(v,(int,float,str,list,tuple)) for v in cfg):raise ValueError("Invalid checkpoint configuration")
  if cfg[2]>512 or cfg[3]>1024 or cfg[4]>4096 or cfg[6]>24 or cfg[15]>1000:raise ValueError("Checkpoint exceeds supported architecture size")
  cfg[-3]=c["weight"]["emb_g.weight"].shape[0]
  if cfg[-3]>1000:raise ValueError("Invalid speaker count")
  self.sr=int(cfg[-1])
  if self.sr not in (32000,40000,48000):raise ValueError("Unsupported RVC sample rate")
  if self.manifest is not None and self.sr!=self.manifest["sample_rate"]:raise ValueError("Checkpoint sample rate differs from manifest")
  ctor=SynthesizerTrnMs768NSFsid if self.version=="v2" else SynthesizerTrnMs256NSFsid
  self.net=ctor(*cfg,is_half=False);del self.net.enc_q
  result=self.net.load_state_dict(c["weight"],strict=False)
  if result.missing_keys:raise ValueError("Checkpoint has missing inference tensors")
  self.net=self.net.float().eval();self.net.remove_weight_norm()
  use_safetensors=(self.hubert_dir/"model.safetensors").is_file()
  self.encoder=HubertModelWithFinalProj.from_pretrained(str(self.hubert_dir),local_files_only=True,use_safetensors=use_safetensors,attn_implementation="eager").float().eval()
  self.normalize=AutoFeatureExtractor.from_pretrained(str(self.hubert_dir),local_files_only=True).do_normalize
  self.pitch=RMVPE(str(self.rmvpe_path),is_half=False,device="cpu")

 def convert(self,x,sr,p):
  torch=self.torch;p=parameters(p);x16=resample(x,sr,16000)
  if len(x16)<1600:x16=np.pad(x16,(0,1600-len(x16)))
  # Fixed seed makes inference repeatable; one engine is owned by one serial worker.
  torch.manual_seed(0)
  with torch.inference_mode():
   audio=torch.from_numpy(x16.copy()).float();source=audio[None]
   if self.normalize:source=(source-source.mean())/(source.var(unbiased=False)+1e-7).sqrt()
   if self.version=="v1":features=self.encoder.final_proj(self.encoder(source,output_hidden_states=True).hidden_states[9])
   else:features=self.encoder(source).last_hidden_state
   length=len(x16)//160
   features=torch.nn.functional.interpolate(features.transpose(1,2),size=length,mode="nearest").transpose(1,2)
   f0=self.pitch.infer_from_audio(audio,thred=.03)[:length]
   f0=np.pad(f0,(0,max(0,length-len(f0))))
   f0*=2**(p["pitch"]/12)
   if p["autotune"]>.001:
    mask=f0>0;note=69+12*np.log2(np.maximum(f0,1)/440);target=np.round(note)
    # Chromatic pitch correction. Continuous speed blends correction; no scale inference.
    f0[mask]=440*2**((note[mask]+(target[mask]-note[mask])*p["autotune"]*(.1+.9*p["tuneSpeed"])-69)/12)
   mel=1127*np.log1p(f0/700);mn=1127*np.log1p(50/700);mx=1127*np.log1p(1100/700)
   coarse=np.rint(np.clip((mel-mn)*254/(mx-mn)+1,1,255)).astype(np.int64)
   y=self.net.infer(features,torch.tensor([length]),torch.from_numpy(coarse)[None],torch.from_numpy(f0.astype(np.float32))[None],torch.tensor([0]))[0][0,0].float().numpy()
  y=resample(y,self.sr,sr);y=np.pad(y,(0,max(0,len(x)-len(y))))[:len(x)]
  # Preserve unvoiced consonants by blending the aligned input in unvoiced spans.
  voiced=np.interp(np.arange(len(x))/sr,np.arange(len(f0))*.01,(f0>0).astype(float))
  preserve=(1-voiced)*p["consonants"]
  return (y*(1-preserve)+x*preserve).astype(np.float32)

def transform_audio(x,sr,p,model_root=None):
 p=parameters(p);dry=x.copy();gain=10**(p["input"]/20);x=x*gain
 if model_root:
  key=str(model_root)
  if key not in _engines:_engines.clear();_engines[key]=RvcEngine(model_root)
  # 8 s windows, 250 ms context, equal-power overlap for long files.
  engine=_engines[key];chunk=sr*8;context=sr//4;out=np.zeros_like(x)
  for start in range(0,len(x),chunk):
   end=min(len(x),start+chunk);lo=max(0,start-context);hi=min(len(x),end+context)
   converted=engine.convert(x[lo:hi],sr,p);out[start:end]=converted[start-lo:end-lo]
  x=out
 q={**p,"input":0,"output":0,"mix":1}
 if model_root:q["pitch"]=0;q["autotune"]=0
 elif p["autotune"]>0:raise ValueError("Chromatic tuning requires an installed RVC model")
 wet=dsp(x,sr,q)
 return np.clip((dry*(1-p["mix"])+wet*p["mix"])*10**(p["output"]/20),-1,1)
_engines={}

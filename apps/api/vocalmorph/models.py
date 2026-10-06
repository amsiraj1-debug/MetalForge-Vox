"""Declarative packages only. Never import Python or unpickle arbitrary objects."""
import hashlib, json, os, re, shutil, tempfile, zipfile
from pathlib import Path
ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
BUILTINS = [dict(id="studio-clean",name="Studio Clean",category="Clean",tags=["natural","transparent"],architecture="dsp",version="1.0.0",license="AGPL-3.0-only",description="Transparent processing. No neural voice model.",sample_rate=48000,pitch_range=[50,1100],installed=True),dict(id="copper-drive",name="Copper Drive",category="Rock",tags=["warm","gritty"],architecture="dsp",version="1.0.0",license="AGPL-3.0-only",description="Original saturation and tone preset. No neural voice model.",sample_rate=48000,pitch_range=[50,1100],installed=True),dict(id="prism-air",name="Prism Air",category="Creative",tags=["airy","bright"],architecture="dsp",version="1.0.0",license="AGPL-3.0-only",description="Original airy character preset. No neural voice model.",sample_rate=48000,pitch_range=[50,1100],installed=True)]
def digest(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def safe_path(root,name):
 if not isinstance(name,str) or "\\" in name or ":" in name:raise ValueError("Invalid package path")
 p=(root/name).resolve()
 if p==root.resolve() or root.resolve() not in p.parents:raise ValueError("Path escapes model directory")
 return p

def validate(root,verify=True):
 root=Path(root);raw=(root/"manifest.json").read_text(encoding="utf-8-sig")
 if len(raw)>128000:raise ValueError("Manifest too large")
 m=json.loads(raw)
 required=["id","name","version","architecture","license","consent","sample_rate","pitch_range","files"]
 if any(k not in m for k in required):raise ValueError("Missing required model metadata")
 if not ID.fullmatch(m["id"]) or m["id"] in {v["id"] for v in BUILTINS}:raise ValueError("Invalid or reserved model ID")
 if m["architecture"] not in ("rvc-v1","rvc-v2"):raise ValueError("Only RVC v1/v2 F0 checkpoints are supported")
 if not m["license"].strip() or m["consent"] is not True:raise ValueError("License and voice consent attestation required")
 if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+",m["version"]):raise ValueError("Use a numeric semantic version")
 if m["sample_rate"] not in (32000,40000,48000):raise ValueError("Unsupported RVC sample rate")
 if not isinstance(m["pitch_range"],list) or len(m["pitch_range"])!=2 or not 30<=m["pitch_range"][0]<m["pitch_range"][1]<=2000:raise ValueError("Invalid pitch range")
 required_files={"model.pth","rmvpe.pt","hubert/config.json","hubert/preprocessor_config.json","hubert/model.safetensors"}
 if not required_files.issubset(m["files"]):raise ValueError("Package needs model.pth, rmvpe.pt, and local HuBERT safetensors/config files")
 if len(m["files"])>50:raise ValueError("Too many model files")
 for name,meta in m["files"].items():
  p=safe_path(root,name)
  if p.suffix not in (".pth",".pt",".safetensors",".json",".txt",".wav",".png",".jpg",".webp"):raise ValueError("Unsupported package file type")
  if not isinstance(meta,dict) or not meta.get("license") or not re.fullmatch(r"[a-f0-9]{64}",meta.get("sha256","")):raise ValueError("Every asset needs a SHA-256 checksum and license")
  if not p.is_file() or p.is_symlink():raise ValueError(f"Missing or unsafe asset: {name}")
  if verify and digest(p)!=meta["sha256"]:raise ValueError(f"Checksum mismatch: {name}")
 m["installed"]=True
 return m

def install_zip(source,destination):
 destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(dir=destination) as td:
  root=Path(td)
  with zipfile.ZipFile(source) as z:
   info=z.infolist()
   if len(info)>70 or sum(i.file_size for i in info)>3*1024**3:raise ValueError("Package exceeds file or expanded size limit")
   for i in info:
    if i.is_dir():continue
    if (i.external_attr>>16)&0o170000==0o120000:raise ValueError("Symlink entries are forbidden")
    p=safe_path(root,i.filename);p.parent.mkdir(parents=True,exist_ok=True)
    with z.open(i) as a,p.open("wb") as b:shutil.copyfileobj(a,b)
  m=validate(root)
  target=destination/(m["id"]+"@"+m["version"])
  if target.exists():raise ValueError("This model version is already installed")
  shutil.copytree(root,target)
  return m

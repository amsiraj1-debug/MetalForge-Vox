"""Binary stdio worker. Only the native control thread uses this protocol."""
import os,sys,struct,json,traceback
from pathlib import Path
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root))
os.environ["VOCALMORPH_RVC"]=str(root.parent/"rvc")
os.environ["TORCH_FORCE_WEIGHTS_ONLY_LOAD"]="1"
os.environ["HF_HUB_OFFLINE"]="1"
if os.name=="nt":
 import msvcrt
 msvcrt.setmode(sys.stdin.fileno(),os.O_BINARY);msvcrt.setmode(sys.stdout.fileno(),os.O_BINARY)
reader=sys.stdin.buffer;writer=sys.stdout.buffer
# Third-party diagnostics must never corrupt the protocol stream.
sys.stdout=sys.stderr
import numpy as np
from vocalmorph.engine import RvcEngine,parameters
engine=None
def exact(n):
 b=bytearray()
 while len(b)<n:
  chunk=reader.read(n-len(b))
  if not chunk:raise EOFError
  b.extend(chunk)
 return bytes(b)
def reply(meta,audio=None):
 meta["frames"]=0 if audio is None else len(audio);data=json.dumps(meta).encode();writer.write(struct.pack("<I",len(data)));writer.write(data)
 if audio is not None:writer.write(np.asarray(audio,dtype="<f4").tobytes())
 writer.flush()
while True:
 try:
  n=struct.unpack("<I",exact(4))[0]
  if n>65536:raise ValueError("Oversized header")
  req=json.loads(exact(n));count=int(req.get("frames",0))
  if not 0<=count<=1920000:raise ValueError("Oversized audio block")
  x=np.frombuffer(exact(count*4),dtype="<f4").copy() if count else None
  try:
   if req["op"]=="load":engine=RvcEngine(req["path"]);reply({"ok":True})
   elif req["op"]=="process":
    if engine is None:raise ValueError("No model loaded")
    p=parameters(req.get("parameters",{}));y=engine.convert(x,int(req["sample_rate"]),p);reply({"ok":True},y)
   else:raise ValueError("Unknown operation")
  except Exception as e:traceback.print_exc();reply({"ok":False,"error":str(e)})
 except EOFError:break
 except Exception:traceback.print_exc();break

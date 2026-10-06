"""Package your authorized model assets; no weights are downloaded or supplied."""
import argparse,hashlib,json,zipfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument("folder",type=Path);p.add_argument("--output",type=Path,required=True);args=p.parse_args()
m=json.loads((args.folder/"manifest.json").read_text());m["files"]=m.get("files",{})
for name in ["model.pth","rmvpe.pt","hubert/config.json","hubert/preprocessor_config.json","hubert/model.safetensors"]:
 f=args.folder/name
 if not f.is_file():raise SystemExit("Missing "+name)
 if not m["files"].get(name,{}).get("license"):raise SystemExit("Declare asset license for "+name)
 m["files"][name]["sha256"]=hashlib.file_digest(f.open("rb"),"sha256").hexdigest()
(args.folder/"manifest.json").write_text(json.dumps(m,indent=2))
with zipfile.ZipFile(args.output,"w",zipfile.ZIP_STORED) as z:
 z.write(args.folder/"manifest.json","manifest.json")
 for name in m["files"]:z.write(args.folder/name,name)
print(args.output)

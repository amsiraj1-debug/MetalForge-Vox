import io,json,os,tempfile,zipfile,time
from pathlib import Path
os.environ['VOCALMORPH_DATA']=tempfile.mkdtemp(prefix='vm-test-')
import numpy as np
import soundfile as sf
import pytest
from fastapi.testclient import TestClient
from vocalmorph.main import app,ROOT
from vocalmorph.engine import parameters,cache_key,DEFAULTS,dsp,resolve_model_source
from vocalmorph.models import safe_path,install_zip,validate

def test_cache_hash():
 assert cache_key('abc',{'id':'test','version':'1.0.0'},DEFAULTS)==cache_key('abc',{'version':'1.0.0','id':'test'},dict(reversed(list(DEFAULTS.items()))))
 assert cache_key('abc','v1',{})!=cache_key('abc','v2',{})
 assert cache_key('abc','v1',{})!=cache_key('abc','v1',{'mix':.5})

@pytest.mark.parametrize('values',[{'pitch':25},{'mix':float('nan')},{'unknown':1},{'input':float('inf')}])
def test_parameter_validation(values):
 with pytest.raises(ValueError):parameters(values)

def test_traversal_and_zip_bomb(tmp_path):
 for name in ['../escape','/tmp/escape','a/../../escape','C:\\file','a\\..\\escape']:
  with pytest.raises(ValueError):safe_path(tmp_path,name)
 z=io.BytesIO()
 with zipfile.ZipFile(z,'w') as f:f.writestr('../escape.py','bad')
 z.seek(0)
 with pytest.raises(ValueError):install_zip(z,tmp_path)

def test_missing_manifest_fields(tmp_path):
 (tmp_path/'manifest.json').write_text('{}')
 with pytest.raises(ValueError):validate(tmp_path)

def test_direct_pth_resolution_without_manifest(tmp_path):
 p=tmp_path/'voice.pth';p.write_bytes(b'checkpoint-placeholder')
 model,root,manifest=resolve_model_source(p)
 assert model==p and root==tmp_path and manifest is None
 model2,root2,manifest2=resolve_model_source(tmp_path)
 assert model2==p and root2==tmp_path and manifest2 is None

def test_native_dsp():
 x=np.sin(np.arange(4800)*2*np.pi*220/48000).astype('float32')*.2
 y=dsp(x,48000,{'aggression':.8})
 assert y.shape==x.shape and np.isfinite(y).all()
 assert not np.allclose(x,y)

def test_end_to_end_audio_cache_presets():
 x=np.sin(np.arange(9600)*2*np.pi*220/48000).astype('float32')*.2
 stream=io.BytesIO();sf.write(stream,x,48000,format='WAV');data=stream.getvalue()
 with TestClient(app) as client:
  assert client.get('/api/health').status_code==200
  bad=client.post('/api/upload',files={'file':('bad.wav',b'invalid')});assert bad.status_code==422
  silent=io.BytesIO();sf.write(silent,np.zeros(4800),48000,format='WAV');assert client.post('/api/upload',files={'file':('silent.wav',silent.getvalue())}).status_code==422
  source=client.post('/api/upload',files={'file':('test.wav',data)}).json()
  assert source['sample_rate']==48000 and source['channels']==1
  request={'source':source['id'],'model':'studio-clean','parameters':{'aggression':.5}}
  response=client.post('/api/transform',json=request);assert response.status_code==200,response.text
  job=response.json()
  for _ in range(100):
   job=client.get('/api/jobs/'+job['id']).json()
   if job['status'] in ('complete','failed'):break
   time.sleep(.05)
  assert job['status']=='complete',job
  assert client.get(job['url']).content[:4]==b'RIFF'
  assert client.post('/api/transform',json=request).json()['cached'] is True
  p={'name':'My test','category':'Custom','model':'studio-clean','version':'1.0.0','parameters':{'mix':.4}}
  saved=client.post('/api/presets',json=p).json()
  assert saved['parameters']['mix']==.4
  assert any(v['id']==saved['id'] for v in client.get('/api/presets').json())
  assert client.get('/api/models/catalog').json()==[]
  assert client.delete('/api/models/studio-clean/1.0.0').status_code==403

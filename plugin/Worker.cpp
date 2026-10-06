#include "Worker.h"
#include <windows.h>
#include <vector>
namespace {
juce::File resources(){HMODULE module=nullptr;GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,reinterpret_cast<LPCWSTR>(&resources),&module);wchar_t path[32768]{};GetModuleFileNameW(module,path,32768);return juce::File(juce::String(path)).getParentDirectory().getParentDirectory().getChildFile("Resources");}
class WorkerProcess {
 HANDLE process=nullptr,readPipe=nullptr,writePipe=nullptr;
public:
 ~WorkerProcess(){close();}
 void close(){if(process){TerminateProcess(process,0);WaitForSingleObject(process,3000);CloseHandle(process);process=nullptr;}if(readPipe){CloseHandle(readPipe);readPipe=nullptr;}if(writePipe){CloseHandle(writePipe);writePipe=nullptr;}}
 bool start(){close();auto root=resources();auto python=root.getChildFile("runtime/python.exe");auto script=root.getChildFile("worker/worker.py");if(!python.existsAsFile()||!script.existsAsFile())return false;
 SECURITY_ATTRIBUTES sa{sizeof(SECURITY_ATTRIBUTES),nullptr,TRUE};HANDLE inRead=nullptr,outWrite=nullptr;
 if(!CreatePipe(&inRead,&writePipe,&sa,1024*1024))return false;
 if(!CreatePipe(&readPipe,&outWrite,&sa,1024*1024)){CloseHandle(inRead);close();return false;}
 SetHandleInformation(writePipe,HANDLE_FLAG_INHERIT,0);SetHandleInformation(readPipe,HANDLE_FLAG_INHERIT,0);
 auto log=juce::File::getSpecialLocation(juce::File::userApplicationDataDirectory).getChildFile("VocalMorph");log.createDirectory();auto logName=log.getChildFile("worker-"+juce::String(GetCurrentProcessId())+"-"+juce::String::toHexString(reinterpret_cast<juce::pointer_sized_int>(this))+".log");
 HANDLE err=CreateFileW(logName.getFullPathName().toWideCharPointer(),GENERIC_WRITE,FILE_SHARE_READ,&sa,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
 STARTUPINFOW si{};si.cb=sizeof(si);si.dwFlags=STARTF_USESTDHANDLES;si.hStdInput=inRead;si.hStdOutput=outWrite;si.hStdError=err;PROCESS_INFORMATION pi{};
 auto command="\""+python.getFullPathName()+"\" -I \""+script.getFullPathName()+"\"";std::wstring cmd(command.toWideCharPointer());
 BOOL ok=CreateProcessW(python.getFullPathName().toWideCharPointer(),cmd.data(),nullptr,nullptr,TRUE,CREATE_NO_WINDOW,nullptr,root.getFullPathName().toWideCharPointer(),&si,&pi);
 CloseHandle(inRead);CloseHandle(outWrite);if(err!=INVALID_HANDLE_VALUE)CloseHandle(err);
 if(!ok){close();return false;}process=pi.hProcess;CloseHandle(pi.hThread);return true;}
 bool write(const void* data,size_t bytes){auto p=static_cast<const char*>(data);while(bytes){DWORD sent=0;if(!WriteFile(writePipe,p,static_cast<DWORD>(std::min<size_t>(bytes,65536)),&sent,nullptr)||sent==0)return false;p+=sent;bytes-=sent;}return true;}
 bool read(void* data,size_t bytes,const std::atomic<bool>& stop){auto p=static_cast<char*>(data);auto deadline=juce::Time::getMillisecondCounterHiRes()+180000.;while(bytes&&!stop){DWORD avail=0;if(!PeekNamedPipe(readPipe,nullptr,0,nullptr,&avail,nullptr))return false;if(avail==0){if(WaitForSingleObject(process,0)==WAIT_OBJECT_0||juce::Time::getMillisecondCounterHiRes()>deadline)return false;std::this_thread::sleep_for(std::chrono::milliseconds(2));continue;}DWORD got=0;if(!ReadFile(readPipe,p,static_cast<DWORD>(std::min<size_t>(bytes,avail)),&got,nullptr)||!got)return false;p+=got;bytes-=got;}return bytes==0;}
 bool request(const juce::var& header,const std::vector<float>& audio,juce::var& reply,std::vector<float>& result,const std::atomic<bool>& stop){auto json=juce::JSON::toString(header,true);uint32_t n=static_cast<uint32_t>(json.getNumBytesAsUTF8());if(!write(&n,4)||!write(json.toRawUTF8(),n)||(!audio.empty()&&!write(audio.data(),audio.size()*4)))return false;
 if(!read(&n,4,stop)||n>65536)return false;std::vector<char> text(n+1,0);if(!read(text.data(),n,stop))return false;reply=juce::JSON::parse(juce::String::fromUTF8(text.data(),static_cast<int>(n)));int count=reply.getProperty("frames",0);if(count<0||count>1920000)return false;result.resize(static_cast<size_t>(count));return result.empty()||read(result.data(),result.size()*4,stop);}
};
}
NeuralWorker::NeuralWorker(){for(size_t i=0;i<vm::parameterCount;++i)params[i]=vm::defaults[i];thread=std::thread([this]{run();});}
NeuralWorker::~NeuralWorker(){stopping=true;if(thread.joinable())thread.join();}
void NeuralWorker::setStatus(juce::String s){std::lock_guard<std::mutex> l(statusMutex);message=std::move(s);}
juce::String NeuralWorker::status(){std::lock_guard<std::mutex> l(statusMutex);return message;}
void NeuralWorker::select(const juce::File& file,double sr){std::lock_guard<std::mutex> l(configMutex);pendingPath=file.getFullPathName();rate=sr;changed=true;loaded=false;++generation;}
void NeuralWorker::run(){WorkerProcess process;double sr=48000;std::vector<vm::TimedSample> chunk;std::vector<float> history,audio,result;juce::var reply;uint32_t active=0;size_t frames=7680;
 while(!stopping){juce::String path;bool reload=false;{std::lock_guard<std::mutex> l(configMutex);if(changed){reload=true;changed=false;path=pendingPath;sr=rate;active=generation.load();}}
 if(reload){loaded=false;chunk.clear();history.clear();process.close();frames=static_cast<size_t>(std::max(128.,sr*.16));if(path.isEmpty()){setStatus("DSP monitoring");continue;}setStatus("Loading RVC model + bundled RMVPE/HuBERT…");if(!process.start()){setStatus("Bundled runtime missing. Install the full release package.");continue;}
 auto* h=new juce::DynamicObject();h->setProperty("op","load");h->setProperty("path",path);if(!process.request(juce::var(h),{},reply,result,stopping)||!static_cast<bool>(reply.getProperty("ok",false))){setStatus("Model load failed: "+reply.getProperty("error","worker unavailable").toString());process.close();continue;}loaded=true;setStatus("Neural model ready · RMVPE · CPU");}
 vm::TimedSample v;if(!loaded){while(input.pop(v)){}std::this_thread::sleep_for(std::chrono::milliseconds(5));continue;}
 while(chunk.size()<frames&&input.pop(v)){if(v.generation!=active)continue;if(!chunk.empty()&&v.time!=chunk.back().time+1){chunk.clear();history.clear();}chunk.push_back(v);}
 if(chunk.size()<frames){std::this_thread::sleep_for(std::chrono::milliseconds(2));continue;}
 auto* h=new juce::DynamicObject();h->setProperty("op","process");h->setProperty("sample_rate",sr);h->setProperty("frames",static_cast<int>(history.size()+chunk.size()));auto* p=new juce::DynamicObject();for(size_t i=0;i<vm::parameterCount;++i)p->setProperty(vm::ids[i],params[i].load());h->setProperty("parameters",juce::var(p));audio=history;for(const auto& s:chunk)audio.push_back(s.value);
 auto t=juce::Time::getMillisecondCounterHiRes();bool ok=process.request(juce::var(h),audio,reply,result,stopping);
 if(!ok||!static_cast<bool>(reply.getProperty("ok",false))||result.size()!=audio.size()){loaded=false;setStatus("Inference stopped: "+reply.getProperty("error","invalid worker response").toString());chunk.clear();continue;}
 for(size_t i=0;i<chunk.size();++i)output.push({result[history.size()+i],chunk[i].time,active});
 size_t keep=std::min(audio.size(),frames*2);history.assign(audio.end()-static_cast<std::ptrdiff_t>(keep),audio.end());chunk.clear();auto ms=juce::Time::getMillisecondCounterHiRes()-t;setStatus("RMVPE · "+juce::String(ms,0)+" ms / 160 ms block"+(ms>160?" · CPU cannot keep up":""));
 }
}

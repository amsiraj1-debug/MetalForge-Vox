#include "vocalmorph/Core.h"
#ifdef _WIN32
#define VM_EXPORT __declspec(dllexport)
#else
#define VM_EXPORT __attribute__((visibility("default")))
#endif
extern "C" VM_EXPORT int vm_process(float* audio,size_t frames,double sr,const float* params,size_t count) {
 if(!audio||!params||count!=vm::parameterCount||sr<8000||sr>192000)return 1;
 try {vm::Dsp dsp;dsp.prepare(sr);vm::Parameters p;std::copy_n(params,count,p.values.begin());p.sanitize();dsp.process(audio,frames,p);return 0;}catch(...){return 2;}
}

#include "vocalmorph/Core.h"
namespace vm {
void Dsp::prepare(double rate){sr=std::clamp(rate,8000.0,192000.0);delay.assign(static_cast<size_t>(sr*.1)+8,0);reset();}
void Dsp::reset() noexcept {std::fill(delay.begin(),delay.end(),0);pos=0;phase=0;low=mid=high=env=prev=dc=0;smooth=defaults;}
float Dsp::tap(double distance) const noexcept {double ix=static_cast<double>(pos)-distance;while(ix<0)ix+=delay.size();auto a=static_cast<size_t>(ix)%delay.size();auto b=(a+1)%delay.size();float f=static_cast<float>(ix-std::floor(ix));return delay[a]*(1-f)+delay[b]*f;}
float Dsp::tick(float source,const Parameters& p) noexcept {
 if(delay.empty())return source;
 for(size_t i=0;i<parameterCount;++i) smooth[i]+=(p.values[i]-smooth[i])*static_cast<float>(1-std::exp(-1/(sr*.015)));
 const auto& v=smooth;float x=std::isfinite(source)?source:0;float dry=x;x*=std::pow(10.f,v[13]/20.f);
 // Dual overlapping delay grains; bypass at unity avoids gratuitous pitch latency.
 delay[pos]=x;
 if(std::abs(v[0])>.01f){double win=sr*.035;double ratio=std::pow(2.,v[0]/12.);phase+=(1-ratio)/win;phase-=std::floor(phase);double q=phase+.5;q-=std::floor(q);float w=static_cast<float>(.5-.5*std::cos(6.283185307179586*phase));x=tap(32+phase*win)*w+tap(32+q*win)*(1-w);}
 pos=(pos+1)%delay.size();
 float aLow=static_cast<float>(1-std::exp(-6.2831853*220/sr));float aMid=static_cast<float>(1-std::exp(-6.2831853*(1800*std::pow(2.,v[1]/12.))/sr));float aHigh=static_cast<float>(1-std::exp(-6.2831853*6500/sr));
 low+=aLow*(x-low);mid+=aMid*(x-mid);high+=aHigh*(x-high);
 float upper=x-high;float voiced=mid-low;
 x+=low*v[4]*1.5f+(x-mid)*v[3]*.8f+upper*v[5]*1.4f+voiced*v[1]/24.f;
 // Consonant preservation offsets de-essing and smoothing on fast transients.
 float consonant=std::clamp(std::abs(x-prev)*8.f,0.f,1.f)*v[10];prev=x;
 x-=upper*v[11]*(1-consonant);x=x*(1-v[7]*.6f)+mid*v[7]*.6f;
 float level=std::abs(x);env+=(level-env)*(level>env?.02f:.0005f);
 float compress=1/(1+std::max(0.f,env-.15f)*v[8]*6.f);x*=compress*(1+v[8]*.4f);
 x*=1+(v[2]-.5f)*std::clamp((env-.1f)*2.f,-.5f,.5f);
 x+=upper*v[9]*.35f;
 if(v[6]>.001f){float drive=1+v[6]*10;float distorted=std::tanh(x*drive)/std::sqrt(drive);x=x*(1-v[6])+distorted*v[6];}
 dc+=static_cast<float>(1-std::exp(-6.2831853*10/sr))*(x-dc);x-=dc;
 float out=(dry*(1-v[12])+x*v[12])*std::pow(10.f,v[14]/20.f);
 return std::isfinite(out)?std::clamp(out,-4.f,4.f):0.f;
}
void Dsp::process(float* x,size_t n,const Parameters& p) noexcept {for(size_t i=0;i<n;++i)x[i]=tick(x[i],p);}
float detectPitch(const float* x,size_t n,double rate) noexcept {
 if(n<64)return 0;size_t lo=static_cast<size_t>(rate/1100),hi=std::min(n/2,static_cast<size_t>(rate/50));float best=0;size_t lag=0;
 for(size_t k=lo;k<=hi;++k){double sum=0,a=0,b=0;for(size_t i=0;i<n-k;++i){sum+=x[i]*x[i+k];a+=x[i]*x[i];b+=x[i+k]*x[i+k];}float score=static_cast<float>(sum/std::sqrt(a*b+1e-20));if(score>best){best=score;lag=k;}if(best>.97f&&score<best*.98f)break;}
 return best>.7f&&lag?static_cast<float>(rate/lag):0;
}
}

#include "vocalmorph/Core.h"
#include <iostream>
#include <thread>
#include <stdexcept>
#define CHECK(x) do{if(!(x))throw std::runtime_error(#x);}while(false)
int main(){try{
 vm::Parameters p;p.values[0]=100;p.sanitize();CHECK(p.values[0]==24);
 vm::Dsp d;d.prepare(48000);p={};for(int i=0;i<10000;++i)CHECK(d.tick(0,p)==0);
 std::vector<float> sine(4096);for(size_t i=0;i<sine.size();++i)sine[i]=.5f*std::sin(6.2831853f*220*i/48000);CHECK(std::abs(vm::detectPitch(sine.data(),sine.size(),48000)-220)<3);
 p.values[6]=1;d.process(sine.data(),sine.size(),p);for(auto f:sine)CHECK(std::isfinite(f));
 vm::Spsc<int,1024> q;std::atomic<bool> ok{true};std::thread producer([&]{for(int i=0;i<100000;++i)while(!q.push(i))std::this_thread::yield();});for(int i=0;i<100000;++i){int v;while(!q.pop(v))std::this_thread::yield();if(v!=i)ok=false;}producer.join();CHECK(ok);CHECK(q.size()==0);
 d.prepare(96000);CHECK(std::isfinite(d.tick(1,p)));std::cout<<"Core DSP, pitch, parameter bounds and SPSC stress passed\n";
 }catch(const std::exception& e){std::cerr<<e.what();return 1;}return 0;}

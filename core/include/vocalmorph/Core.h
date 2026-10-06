#pragma once
#include <array>
#include <atomic>
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <vector>
namespace vm {
constexpr size_t parameterCount=17;
inline constexpr std::array<const char*,parameterCount> ids={"pitch","formant","expression","brightness","body","air","aggression","smoothness","dynamics","breath","consonants","sibilance","mix","input","output","autotune","tuneSpeed"};
inline constexpr std::array<float,parameterCount> defaults={0,0,0.5f,0,0,0,0,0,0,0,0.5f,0,1,0,0,0,0.5f};
inline constexpr std::array<float,parameterCount> minimum={-24,-12,0,-1,-1,0,0,0,0,0,0,0,0,-24,-24,0,0};
inline constexpr std::array<float,parameterCount> maximum={24,12,1,1,1,1,1,1,1,1,1,1,1,24,24,1,1};
struct Parameters { std::array<float,parameterCount> values=defaults; void sanitize() noexcept {for(size_t i=0;i<parameterCount;++i) values[i]=std::isfinite(values[i])?std::clamp(values[i],minimum[i],maximum[i]):defaults[i];} };
class Dsp {
public:
 void prepare(double sampleRate);
 void reset() noexcept;
 float tick(float input,const Parameters& p) noexcept;
 void process(float* data,size_t count,const Parameters& p) noexcept;
private:
 double sr=48000; std::array<float,parameterCount> smooth=defaults;
 std::vector<float> delay; size_t pos=0; double phase=0;
 float low=0,mid=0,high=0,env=0,prev=0,dc=0;
 float tap(double distance) const noexcept;
};
float detectPitch(const float* x,size_t n,double sr) noexcept;
// Single producer / single consumer. Never clear while either endpoint is running.
template<typename T,size_t Capacity> class Spsc {
 static_assert((Capacity&(Capacity-1))==0,"Power-of-two capacity required");
 std::array<T,Capacity> storage{};
 alignas(64) std::atomic<size_t> write{0};
 alignas(64) std::atomic<size_t> read{0};
public:
 bool push(const T& v) noexcept {auto w=write.load(std::memory_order_relaxed);if(w-read.load(std::memory_order_acquire)==Capacity)return false;storage[w&(Capacity-1)]=v;write.store(w+1,std::memory_order_release);return true;}
 bool pop(T& v) noexcept {auto r=read.load(std::memory_order_relaxed);if(r==write.load(std::memory_order_acquire))return false;v=storage[r&(Capacity-1)];read.store(r+1,std::memory_order_release);return true;}
 size_t size() const noexcept {return write.load(std::memory_order_acquire)-read.load(std::memory_order_acquire);}
};
struct TimedSample {float value=0;uint64_t time=0;uint32_t generation=0;};
}

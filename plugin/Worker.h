#pragma once
#include <JuceHeader.h>
#include "vocalmorph/Core.h"
#include <thread>
#include <mutex>
class NeuralWorker {
public:
 NeuralWorker();~NeuralWorker();
 vm::Spsc<vm::TimedSample,262144> input,output;
 std::atomic<uint32_t> generation{1};
 std::array<std::atomic<float>,vm::parameterCount> params;
 void select(const juce::File& file,double sampleRate);
 juce::String status();
 bool ready() const {return loaded.load();}
private:
 std::atomic<bool> stopping{false},loaded{false};
 std::mutex configMutex,statusMutex;juce::String pendingPath,message="DSP monitoring · no neural model loaded";double rate=48000;bool changed=false;
 std::thread thread;
 void run();void setStatus(juce::String s);
};

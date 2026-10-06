#pragma once
#include <JuceHeader.h>
#include "Worker.h"
class VocalMorphProcessor:public juce::AudioProcessor {
public:
 VocalMorphProcessor();~VocalMorphProcessor() override=default;
 void prepareToPlay(double,int) override;void releaseResources() override{};
 void processBlock(juce::AudioBuffer<float>&,juce::MidiBuffer&) override;
 void processBlockBypassed(juce::AudioBuffer<float>&,juce::MidiBuffer&) override;
 bool isBusesLayoutSupported(const BusesLayout&) const override;
 juce::AudioProcessorEditor* createEditor() override;bool hasEditor() const override{return true;}
 const juce::String getName() const override{return "VocalMorph";}
 bool acceptsMidi() const override{return false;}bool producesMidi() const override{return false;}bool isMidiEffect() const override{return false;}
 double getTailLengthSeconds() const override{return .1;}
 int getNumPrograms() override{return 1;}int getCurrentProgram() override{return 0;}void setCurrentProgram(int) override{}
 const juce::String getProgramName(int) override{return "Current";}void changeProgramName(int,const juce::String&) override{}
 void getStateInformation(juce::MemoryBlock&) override;void setStateInformation(const void*,int) override;
 void selectModel(juce::File);void setNeuralMode(bool);
 juce::AudioProcessorValueTreeState state;
 NeuralWorker worker;
 vm::Spsc<float,2048> meter;
 std::atomic<int> underruns{0};std::atomic<bool> neural{false};juce::String modelPath;
 static juce::AudioProcessorValueTreeState::ParameterLayout layout();
private:
 std::array<std::atomic<float>*,vm::parameterCount> raw{};
 std::array<vm::Dsp,2> dsp;std::array<std::vector<float>,2> dry;
 uint64_t clock=0;size_t dryPos=0;int latency=0;double rate=48000;vm::TimedSample pending{};bool hasPending=false;
 void process(juce::AudioBuffer<float>&,bool bypass);
 JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(VocalMorphProcessor)
};

#pragma once
#include "Processor.h"
class MorphLook:public juce::LookAndFeel_V4 {
public:MorphLook();void drawRotarySlider(juce::Graphics&,int,int,int,int,float,float,float,juce::Slider&) override;
};
class VocalMorphEditor:public juce::AudioProcessorEditor,private juce::Timer {
public:explicit VocalMorphEditor(VocalMorphProcessor&);~VocalMorphEditor() override;void paint(juce::Graphics&) override;void resized() override;
private:
 VocalMorphProcessor& processor;MorphLook look;
 std::array<juce::Slider,vm::parameterCount> knobs;std::array<juce::Label,vm::parameterCount> labels;
 std::vector<std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment>> attachments;
 juce::TextButton load{"Import model / .pth"},save{"Save preset"},open{"Load preset"};juce::ComboBox mode,factory;
 juce::Label status,model;std::unique_ptr<juce::FileChooser> chooser;std::array<float,256> waveform{};size_t wavePos=0;
 void timerCallback() override;
 JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(VocalMorphEditor)
};

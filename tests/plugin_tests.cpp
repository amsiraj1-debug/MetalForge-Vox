#include "Processor.h"
#include <memory>
#include <cmath>

int main()
{
    juce::ScopedJuceInitialiser_GUI gui;

    auto p = std::make_unique<VocalMorphProcessor>();
    p->prepareToPlay(48000.0, 512);

    juce::AudioBuffer<float> buffer(2, 512);
    buffer.clear();
    juce::MidiBuffer midi;
    p->processBlock(buffer, midi);
    if (buffer.getMagnitude(0, 512) != 0.0f)
        return 1;

    auto* mix = p->state.getParameter("mix");
    mix->setValueNotifyingHost(0.37f);

    juce::MemoryBlock state;
    p->getStateInformation(state);

    auto q = std::make_unique<VocalMorphProcessor>();
    q->setStateInformation(state.getData(), static_cast<int>(state.getSize()));
    if (std::abs(q->state.getRawParameterValue("mix")->load() - 0.37f) > 0.001f)
        return 2;

    q->prepareToPlay(96000.0, 128);
    q->processBlock(buffer, midi);
    q->setNeuralMode(true);
    if (q->getLatencySamples() != 61440)
        return 3;

    // Neural mode must never leak the original/dry voice while converted audio is unavailable.
    auto wetOnly = std::make_unique<VocalMorphProcessor>();
    wetOnly->prepareToPlay(48000.0, 32768);
    wetOnly->setNeuralMode(true);
    juce::AudioBuffer<float> voice(2, 32768);
    voice.clear();
    for (int c = 0; c < voice.getNumChannels(); ++c)
        for (int n = 0; n < voice.getNumSamples(); ++n)
            voice.setSample(c, n, 0.25f);
    wetOnly->processBlock(voice, midi);
    if (voice.getMagnitude(0, voice.getNumSamples()) != 0.0f ||
        voice.getMagnitude(1, voice.getNumSamples()) != 0.0f)
        return 4;

    // Late converted samples must still be played in FIFO order after the neural buffer.
    auto fifo = std::make_unique<VocalMorphProcessor>();
    fifo->prepareToPlay(48000.0, 30720);
    fifo->setNeuralMode(true);
    juce::AudioBuffer<float> preroll(2, 30720);
    preroll.clear();
    fifo->processBlock(preroll, midi);
    auto generation = fifo->worker.generation.load();
    for (int i = 0; i < 512; ++i)
        fifo->worker.output.push({0.2f, 0, generation});
    juce::AudioBuffer<float> converted(2, 512);
    converted.clear();
    fifo->processBlock(converted, midi);
    if (converted.getMagnitude(0, converted.getNumSamples()) <= 0.0f)
        return 5;

    return 0;
}

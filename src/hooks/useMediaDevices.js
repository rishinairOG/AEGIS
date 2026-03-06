import { useState, useEffect } from 'react';

/**
 * Microphone, speaker, webcam device lists and selected IDs with localStorage persistence.
 */
export function useMediaDevices() {
    const [micDevices, setMicDevices] = useState([]);
    const [speakerDevices, setSpeakerDevices] = useState([]);
    const [webcamDevices, setWebcamDevices] = useState([]);
    const [selectedMicId, setSelectedMicId] = useState(() => localStorage.getItem('selectedMicId') || '');
    const [selectedSpeakerId, setSelectedSpeakerId] = useState(() => localStorage.getItem('selectedSpeakerId') || '');
    const [selectedWebcamId, setSelectedWebcamId] = useState(() => localStorage.getItem('selectedWebcamId') || '');

    useEffect(() => {
        navigator.mediaDevices.enumerateDevices().then(devs => {
            const audioInputs = devs.filter(d => d.kind === 'audioinput');
            const audioOutputs = devs.filter(d => d.kind === 'audiooutput');
            const videoInputs = devs.filter(d => d.kind === 'videoinput');
            setMicDevices(audioInputs);
            setSpeakerDevices(audioOutputs);
            setWebcamDevices(videoInputs);
            const savedMicId = localStorage.getItem('selectedMicId');
            if (savedMicId && audioInputs.some(d => d.deviceId === savedMicId)) {
                setSelectedMicId(savedMicId);
            } else if (audioInputs.length > 0) {
                setSelectedMicId(audioInputs[0].deviceId);
            }
            const savedSpeakerId = localStorage.getItem('selectedSpeakerId');
            if (savedSpeakerId && audioOutputs.some(d => d.deviceId === savedSpeakerId)) {
                setSelectedSpeakerId(savedSpeakerId);
            } else if (audioOutputs.length > 0) {
                setSelectedSpeakerId(audioOutputs[0].deviceId);
            }
            const savedWebcamId = localStorage.getItem('selectedWebcamId');
            if (savedWebcamId && videoInputs.some(d => d.deviceId === savedWebcamId)) {
                setSelectedWebcamId(savedWebcamId);
            } else if (videoInputs.length > 0) {
                setSelectedWebcamId(videoInputs[0].deviceId);
            }
        });
    }, []);

    useEffect(() => {
        if (selectedMicId) localStorage.setItem('selectedMicId', selectedMicId);
    }, [selectedMicId]);
    useEffect(() => {
        if (selectedSpeakerId) localStorage.setItem('selectedSpeakerId', selectedSpeakerId);
    }, [selectedSpeakerId]);
    useEffect(() => {
        if (selectedWebcamId) localStorage.setItem('selectedWebcamId', selectedWebcamId);
    }, [selectedWebcamId]);

    return {
        micDevices,
        speakerDevices,
        webcamDevices,
        selectedMicId,
        setSelectedMicId,
        selectedSpeakerId,
        setSelectedSpeakerId,
        selectedWebcamId,
        setSelectedWebcamId
    };
}

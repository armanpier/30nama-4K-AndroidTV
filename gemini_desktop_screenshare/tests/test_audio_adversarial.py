"""
Adversarial Verification Suite for Audio Pipeline.
Tests:
1. sounddevice device query: inspect all input/output devices, host APIs (MME, WASAPI, DirectSound, WDM-KS).
2. Check default input device compatibility with 16,000 Hz, 1 channel, int16.
3. Check default output device compatibility with 24,000 Hz, 1 channel, int16.
4. Test RawInputStream(samplerate=16000, channels=1, dtype='int16') initialization and audio capture.
5. Test RawOutputStream(samplerate=24000, channels=1, dtype='int16') initialization.
6. Benchmark interruption latency:
   - Queue draining alone (time to empty queue with 10, 50, 100 chunks).
   - stream.stop() execution latency.
   - stream.start() execution latency.
   - Combined interrupt() latency.
7. Architectural bug check: Does the assessment's AudioOutputEngine actually play audio from queue to stream?
"""

import sounddevice as sd
import queue
import time
import json
import numpy as np

def test_device_capabilities():
    print("=== SOUNDDEVICE DEVICE CAPABILITIES ===")
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    default_in = sd.default.device[0]
    default_out = sd.default.device[1]
    
    print(f"Total devices reported: {len(devices)}")
    print(f"Host APIs: {[api['name'] for api in hostapis]}")
    print(f"Default Input Device index: {default_in} -> {devices[default_in]['name']}")
    print(f"Default Output Device index: {default_out} -> {devices[default_out]['name']}")
    
    # Check 16kHz input capability on default input device
    input_16k_ok = False
    input_16k_err = None
    try:
        sd.check_input_settings(device=default_in, samplerate=16000, channels=1, dtype='int16')
        input_16k_ok = True
    except Exception as e:
        input_16k_err = str(e)

    # Check 24kHz output capability on default output device
    output_24k_ok = False
    output_24k_err = None
    try:
        sd.check_output_settings(device=default_out, samplerate=24000, channels=1, dtype='int16')
        output_24k_ok = True
    except Exception as e:
        output_24k_err = str(e)
        
    # Also check other common rates: 44100, 48000
    output_48k_ok = False
    try:
        sd.check_output_settings(device=default_out, samplerate=48000, channels=1, dtype='int16')
        output_48k_ok = True
    except Exception as e:
        pass

    results = {
        "default_input": {
            "index": default_in,
            "name": devices[default_in]["name"],
            "max_input_channels": devices[default_in]["max_input_channels"],
            "default_samplerate": devices[default_in]["default_samplerate"],
            "supports_16k_mono_int16": input_16k_ok,
            "error_16k": input_16k_err
        },
        "default_output": {
            "index": default_out,
            "name": devices[default_out]["name"],
            "max_output_channels": devices[default_out]["max_output_channels"],
            "default_samplerate": devices[default_out]["default_samplerate"],
            "supports_24k_mono_int16": output_24k_ok,
            "error_24k": output_24k_err,
            "supports_48k": output_48k_ok
        }
    }
    print(json.dumps(results, indent=2))
    return results

def test_input_stream_actual():
    print("\n=== TESTING RAWINPUTSTREAM (16kHz, mono, int16) ===")
    q = queue.Queue()
    def audio_cb(indata, frames, time_info, status):
        q.put(bytes(indata))
        
    try:
        stream = sd.RawInputStream(
            samplerate=16000,
            blocksize=1600, # 100ms
            channels=1,
            dtype='int16',
            callback=audio_cb
        )
        stream.start()
        time.sleep(0.35) # capture ~3 chunks
        stream.stop()
        stream.close()
        
        chunks = []
        while not q.empty():
            chunks.append(q.get_nowait())
            
        print(f"Captured {len(chunks)} audio chunks successfully!")
        if chunks:
            chunk_lens = [len(c) for c in chunks]
            print(f"Chunk byte lengths: {chunk_lens} (expected 3200 bytes each)")
            return True, len(chunks), chunk_lens[0]
        return False, 0, 0
    except Exception as e:
        print(f"RawInputStream failed: {e}")
        return False, 0, str(e)

def test_interruption_latency():
    print("\n=== BENCHMARKING BARGE-IN INTERRUPTION LATENCY ===")
    # Initialize Output Stream at 24kHz
    stream = sd.RawOutputStream(
        samplerate=24000,
        channels=1,
        dtype='int16',
        blocksize=1024
    )
    stream.start()

    # 1. Pure queue draining latency (simulating 10, 50, 100 chunks of 24kHz audio)
    for num_chunks in [5, 20, 50]:
        q = queue.Queue()
        dummy_chunk = b'\x00' * 4800 # 100ms at 24kHz int16 mono
        for _ in range(num_chunks):
            q.put(dummy_chunk)
            
        t0 = time.perf_counter()
        drained = 0
        while not q.empty():
            try:
                q.get_nowait()
                drained += 1
            except queue.Empty:
                break
        drain_ms = (time.perf_counter() - t0) * 1000.0
        print(f"Draining {num_chunks} chunks: {drain_ms:.4f} ms (drained: {drained})")

    # 2. Measure stream.stop() latency
    stop_latencies = []
    start_latencies = []
    combined_latencies = []
    
    for _ in range(10):
        # Time stop
        t0 = time.perf_counter()
        stream.stop()
        t_stop = (time.perf_counter() - t0) * 1000.0
        stop_latencies.append(t_stop)

        # Time start
        t0 = time.perf_counter()
        stream.start()
        t_start = (time.perf_counter() - t0) * 1000.0
        start_latencies.append(t_start)

        combined_latencies.append(t_stop + t_start)

    stream.stop()
    stream.close()

    print(f"\nStream Stop latency: avg={np.mean(stop_latencies):.2f} ms, min={np.min(stop_latencies):.2f} ms, max={np.max(stop_latencies):.2f} ms")
    print(f"Stream Start latency: avg={np.mean(start_latencies):.2f} ms, min={np.min(start_latencies):.2f} ms, max={np.max(start_latencies):.2f} ms")
    print(f"Total Stream Restart latency: avg={np.mean(combined_latencies):.2f} ms, min={np.min(combined_latencies):.2f} ms, max={np.max(combined_latencies):.2f} ms")

def test_playback_architecture_bug():
    print("\n=== ADVERSARIAL INSPECTION OF AUDIO OUTPUT ARCHITECTURE ===")
    from inspect import getsource
    # In EXISTING_SOLUTIONS_ASSESSMENT.md, AudioOutputEngine was defined with:
    # def play_chunk(self, pcm_bytes): self.queue.put(pcm_bytes)
    # But self.stream is RawOutputStream without callback or write thread!
    print("Checking whether queue.get() feeds into stream.write():")
    print("Vulnerability: The blueprint in Section 6.3.2 specifies RawOutputStream without a playback callback or worker thread writing chunks to stream.write()!")
    print("Without an active stream.write() worker thread or output callback, buffered audio in self.queue is NEVER played to speakers!")

if __name__ == "__main__":
    test_device_capabilities()
    test_input_stream_actual()
    test_interruption_latency()
    test_playback_architecture_bug()

import os
import numpy as np
import pygame
import pyaudio
import wave
import struct
import time
from scipy.fft import fft
from pydub import AudioSegment
import tempfile

class AudioProcessor:
    def __init__(self, file_path=None, mic_mode=False):
        self.file_path = file_path
        self.mic_mode = mic_mode
        self.chunk_size = 1024
        self.format = pyaudio.paInt16
        self.channels = 2
        self.rate = 44100
        
        # Initialize pygame mixer first
        pygame.mixer.init(frequency=self.rate)
        
        # Initialize PyAudio
        try:
            self.p = pyaudio.PyAudio()
        except Exception as e:
            print(f"Error initializing PyAudio: {e}")
            print("Falling back to simplified mode without PyAudio")
            self.p = None
        
        if mic_mode and self.p:
            self._setup_mic()
        elif file_path:
            self._setup_file()
    
    def _setup_mic(self):
        """Set up microphone input"""
        try:
            self.stream = self.p.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            print("Microphone input initialized successfully")
        except Exception as e:
            print(f"Error setting up microphone: {e}")
            self.stream = None
    
    def _setup_file(self):
        """Set up file input"""
        if not os.path.exists(self.file_path):
            print(f"Error: File {self.file_path} not found")
            return
            
        # Load file for playback
        try:
            pygame.mixer.music.load(self.file_path)
            print(f"Loaded {self.file_path} for playback")
        except Exception as e:
            print(f"Error loading file for playback: {e}")
        
        # Try to open wave file for analysis
        try:
            self.wf = wave.open(self.file_path, 'rb')
            self.channels = self.wf.getnchannels()
            self.rate = self.wf.getframerate()
            print(f"Audio info: {self.rate}Hz, {self.channels} channels")
            
            # Create a stream for analysis if PyAudio is available
            if self.p:
                try:
                    self.stream = self.p.open(
                        format=self.p.get_format_from_width(self.wf.getsampwidth()),
                        channels=self.channels,
                        rate=self.rate,
                        output=False,
                        frames_per_buffer=self.chunk_size
                    )
                except Exception as e:
                    print(f"Error creating analysis stream: {e}")
                    self.stream = None
        except Exception as e:
            print(f"Error opening wave file for analysis: {e}")
            print("Will use simulated frequency data")
            self.wf = None
            self.stream = None
    
    def play(self):
        """Start audio playback"""
        try:
            pygame.mixer.music.play()
            print("Playback started")
        except Exception as e:
            print(f"Error starting playback: {e}")
    
    def stop(self):
        """Stop audio playback and clean up"""
        try:
            pygame.mixer.music.stop()
        except:
            pass
        
        # Clean up resources
        if hasattr(self, 'stream') and self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
        
        if hasattr(self, 'wf') and self.wf:
            try:
                self.wf.close()
            except:
                pass
        
        if self.p:
            try:
                self.p.terminate()
            except:
                pass
    
    def get_frequency_data(self):
        """Get frequency data from current audio"""
        # Initialize with zeros
        band_averages = np.zeros(16)
        
        try:
            if self.mic_mode and self.stream:
                # Read from microphone
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                band_averages = self._process_audio_data(data)
            elif not self.mic_mode:
                if self.wf and self.stream:
                    # Try to read from file synchronized with playback
                    try:
                        current_pos = pygame.mixer.music.get_pos() / 1000.0  # Convert to seconds
                        frame_pos = int(current_pos * self.rate)
                        
                        # Seek to current position (approximate)
                        self.wf.setpos(max(0, frame_pos - self.chunk_size))
                        
                        # Read a chunk of data
                        data = self.wf.readframes(self.chunk_size)
                        
                        # If we've reached the end of the file, loop back
                        if len(data) < self.chunk_size * self.channels * 2:
                            self.wf.rewind()
                            data = self.wf.readframes(self.chunk_size)
                        
                        band_averages = self._process_audio_data(data)
                    except Exception as e:
                        print(f"Error reading from wave file: {e}")
                        # Fall back to simulated data
                        band_averages = self._generate_simulated_data()
                else:
                    # Use simulated data if we couldn't open the file for analysis
                    band_averages = self._generate_simulated_data()
        except Exception as e:
            print(f"Error in get_frequency_data: {e}")
        
        return band_averages
    
    def _process_audio_data(self, data):
        """Process raw audio data into frequency bands"""
        try:
            # Convert binary data to numpy array
            count = len(data) // 2
            format_str = f"{count}h"
            data_int = struct.unpack(format_str, data)
            data_np = np.array(data_int, dtype=np.float32) / 32768.0  # Normalize to [-1, 1]
            
            # Apply FFT
            fft_data = fft(data_np)
            fft_data = np.abs(fft_data[:self.chunk_size//2])  # Take only the first half
            
            # Group frequencies into bands (logarithmically spaced)
            num_bands = 16  # Number of frequency bands
            bands = np.logspace(0, np.log10(len(fft_data)), num_bands+1).astype(int)
            bands = np.unique(bands)  # Remove duplicates
            
            # Calculate average amplitude for each band
            band_averages = []
            for i in range(len(bands)-1):
                start, end = bands[i], bands[i+1]
                band_avg = np.mean(fft_data[start:end])
                band_averages.append(band_avg)
            
            # Apply some smoothing and scaling
            band_averages = np.array(band_averages) * 5.0  # Amplify
            band_averages = np.clip(band_averages, 0, 1)   # Clip to [0, 1]
            
            return band_averages
        except Exception as e:
            print(f"Error processing audio data: {e}")
            return np.zeros(16)
    
    def _generate_simulated_data(self):
        """Generate simulated frequency data based on playback position"""
        try:
            if pygame.mixer.music.get_busy():
                pos = pygame.mixer.music.get_pos() / 1000.0
                # Create some pseudo-random but consistent frequency data
                np.random.seed(int(pos * 10))
                base_data = np.random.random(16) * 0.5
                
                # Add some time-based variations
                variations = np.sin(np.linspace(0, 4*np.pi, 16) + pos) * 0.25 + 0.25
                
                # Combine and normalize
                freq_data = base_data + variations
                freq_data = np.clip(freq_data, 0, 1)
                
                return freq_data
            else:
                return np.zeros(16)
        except:
            return np.zeros(16) 
import os
import queue
import re
import threading
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple
import shutil
import subprocess

import numpy as np
import serial
import sounddevice as sd
from faster_whisper import WhisperModel
from sentence_transformers import SentenceTransformer, util

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None


SAMPLE_RATE = 16000
BLOCK_SECONDS = 0.5
WINDOW_SECONDS = 4.0
TRANSCRIBE_INTERVAL = 1.2
MIN_RMS = 0.015
POST_RESPONSE_COOLDOWN = 2.5
TTS_COOLDOWN_SECONDS = 1.0
SERIAL_PORT = os.getenv("PLANT_SERIAL_PORT", "/dev/tty.usbmodem14101")
SERIAL_BAUD = 115200
WHISPER_SIZE = os.getenv("WHISPER_SIZE", "small")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "auto")
WHISPER_COMPUTE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
ENABLE_TTS = os.getenv("PLANT_ENABLE_TTS", "1") == "1"
MACOS_VOICE = os.getenv("PLANT_MACOS_VOICE", "Tingting")
NORMAL_NOD_AMPLITUDE = 30
NORMAL_WIGGLE_AMPLITUDE = 42
SONG_NOD_AMPLITUDE = 34
SONG_WIGGLE_AMPLITUDE = 48


@dataclass
class AnalysisResult:
    text: str
    emotion: str
    emotion_score: float
    intent: str
    intent_score: float
    reply: str
    led: Tuple[int, int, int]
    motion: str
    perform_song: bool = False


class PrototypeClassifier:
    def __init__(self, model_name: str, label_examples: Dict[str, List[str]]):
        self.model = SentenceTransformer(model_name)
        self.labels = list(label_examples.keys())
        self.examples = label_examples
        self.label_embeddings = {}
        for label, sentences in label_examples.items():
            self.label_embeddings[label] = self.model.encode(sentences, convert_to_tensor=True)

    def predict(self, text: str) -> Tuple[str, float]:
        text_embedding = self.model.encode(text, convert_to_tensor=True)
        best_label = "neutral"
        best_score = -1.0
        for label, embeddings in self.label_embeddings.items():
            score = float(util.cos_sim(text_embedding, embeddings).max().item())
            if score > best_score:
                best_label = label
                best_score = score
        return best_label, best_score


class PlantHardware:
    def __init__(self, port: str, baudrate: int):
        self.serial_conn = serial.Serial(port, baudrate, timeout=1)
        time.sleep(2.0)
        self.lock = threading.Lock()

    def send(self, command: str) -> None:
        with self.lock:
            self.serial_conn.write((command.strip() + "\n").encode("utf-8"))
            self.serial_conn.flush()

    def set_led(self, rgb: Tuple[int, int, int]) -> None:
        r, g, b = rgb
        self.send(f"LED {r} {g} {b}")

    def nod(self, cycles: int = 2, center: int = 90, amplitude: int = 18, step_delay_ms: int = 12) -> None:
        self.send(f"NOD {cycles} {center} {amplitude} {step_delay_ms}")

    def wiggle(self, cycles: int = 2, center: int = 90, amplitude: int = 22, step_delay_ms: int = 12) -> None:
        self.send(f"WIGGLE {cycles} {center} {amplitude} {step_delay_ms}")

    def listen_pose(self) -> None:
        self.set_led((80, 160, 255))

    def idle_pose(self) -> None:
        self.set_led((0, 90, 20))
        self.send("SERVO 90 10")

    def flash_led(self, base_rgb: Tuple[int, int, int], flashes: int = 3, flash_delay: float = 0.1) -> None:
        r, g, b = base_rgb
        on_ms = int(flash_delay * 1000)
        off_ms = int(flash_delay * 1000)
        self.send(f"FLASH {r} {g} {b} {flashes} {on_ms} {off_ms}")

    def sleep(self) -> None:
        self.send("SLEEP")


class TalkingPlant:
    def __init__(self):
        self.running = True
        self.audio_queue: "queue.Queue[np.ndarray]" = queue.Queue()
        self.audio_buffer = np.zeros(0, dtype=np.float32)
        self.last_transcribe_time = 0.0
        self.last_text = ""
        self.cooldown_until = 0.0
        self.is_speaking = False

        self.hardware = PlantHardware(SERIAL_PORT, SERIAL_BAUD)
        self.whisper = WhisperModel(
            WHISPER_SIZE,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE,
        )
        self.emotion_classifier = PrototypeClassifier(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            {
                "happy": [
                    "我今天很开心很兴奋",
                    "这太棒了我非常喜欢",
                    "好高兴见到你",
                ],
                "sad": [
                    "我有点难过很失落",
                    "今天心情不太好",
                    "我觉得很沮丧",
                ],
                "angry": [
                    "我现在很生气",
                    "这让我特别烦",
                    "我真的受不了了",
                ],
                "calm": [
                    "我现在很平静",
                    "今天状态很放松",
                    "我只是想随便聊聊",
                ],
                "neutral": [
                    "你好小植物",
                    "今天天气怎么样",
                    "你在做什么",
                ],
            },
        )
        self.intent_classifier = PrototypeClassifier(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            {
                "greeting": [
                    "你好呀",
                    "早上好",
                    "很高兴认识你",
                ],
                "care": [
                    "你今天还好吗",
                    "我来看看你",
                    "我想陪你聊天",
                ],
                "question": [
                    "你觉得怎么样",
                    "你能回答我吗",
                    "我想问你一个问题",
                ],
                "praise": [
                    "你好可爱",
                    "你真棒",
                    "我很喜欢你",
                ],
                "complaint": [
                    "我今天压力很大",
                    "事情太糟糕了",
                    "我现在很烦",
                ],
            },
        )
        self.tts_engine = self._init_tts()
        self.song_keywords = ("唱歌", "唱一首歌", "唱首歌", "给我唱", "两只老虎", "唱两只老虎")
        self.macos_say_available = shutil.which("say") is not None

    def _init_tts(self):
        if not ENABLE_TTS or pyttsx3 is None:
            return None
        engine = pyttsx3.init()
        engine.setProperty("rate", 180)
        engine.setProperty("volume", 0.9)
        return engine

    def speak_text(self, text: str, rate: Optional[int] = None) -> None:
        if not ENABLE_TTS or not text:
            return
        self.is_speaking = True
        self.clear_audio_buffers()
        try:
            if self.macos_say_available:
                say_rate = str(rate or 185)
                subprocess.run(
                    ["say", "-v", MACOS_VOICE, "-r", say_rate, text],
                    check=False,
                )
                return

            if self.tts_engine is None:
                return

            original_rate = self.tts_engine.getProperty("rate")
            try:
                if rate is not None:
                    self.tts_engine.setProperty("rate", rate)
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            finally:
                if rate is not None:
                    self.tts_engine.setProperty("rate", original_rate)
        finally:
            self.clear_audio_buffers()
            self.cooldown_until = time.time() + TTS_COOLDOWN_SECONDS
            self.is_speaking = False

    def audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"[audio-status] {status}")
        mono = np.mean(indata, axis=1).astype(np.float32)
        self.audio_queue.put(mono.copy())

    def clear_audio_buffers(self) -> None:
        self.audio_buffer = np.zeros(0, dtype=np.float32)
        self.audio_queue = queue.Queue()

    def update_audio_buffer(self) -> None:
        while not self.audio_queue.empty():
            chunk = self.audio_queue.get()
            self.audio_buffer = np.concatenate([self.audio_buffer, chunk])
            max_samples = int(SAMPLE_RATE * WINDOW_SECONDS)
            if len(self.audio_buffer) > max_samples:
                self.audio_buffer = self.audio_buffer[-max_samples:]

    def transcribe_audio(self, audio: np.ndarray) -> str:
        if len(audio) < int(SAMPLE_RATE * 1.2):
            return ""

        rms = float(np.sqrt(np.mean(np.square(audio))))
        if rms < MIN_RMS:
            return ""

        segments, _ = self.whisper.transcribe(
            audio,
            language="zh",
            beam_size=1,
            vad_filter=True,
            temperature=0.0,
            condition_on_previous_text=False,
        )
        text = "".join(segment.text for segment in segments).strip()
        text = re.sub(r"\s+", "", text)
        return text

    def is_similar_to_last_text(self, text: str) -> bool:
        if not self.last_text:
            return False
        similarity = SequenceMatcher(None, self.last_text, text).ratio()
        return similarity >= 0.82

    def analyze_text(self, text: str) -> AnalysisResult:
        perform_song = any(keyword in text for keyword in self.song_keywords)
        emotion, emotion_score = self.emotion_classifier.predict(text)
        intent, intent_score = self.intent_classifier.predict(text)

        if emotion == "happy":
            led = (255, 180, 40)
            motion = "wiggle"
            reply = "听起来你现在很开心，我也跟着摇摇叶子。"
        elif emotion == "sad":
            led = (70, 120, 255)
            motion = "nod"
            reply = "我在这里陪着你，慢一点也没关系。"
        elif emotion == "angry":
            led = (255, 50, 30)
            motion = "nod"
            reply = "我听见你的烦躁了，先一起深呼吸一下。"
        elif emotion == "calm":
            led = (60, 220, 140)
            motion = "wiggle"
            reply = "你的状态很放松，我也轻轻晃一晃。"
        else:
            led = (120, 255, 120)
            motion = "wiggle"
            reply = "我听到了，我们继续聊。"

        if intent == "greeting":
            reply = "你好呀，我已经醒啦，正在认真听你说话。"
        elif intent == "praise":
            reply = "被你夸奖到啦，我给你亮一点绿色。"
            led = (80, 255, 100)
            motion = "wiggle"
        elif intent == "care":
            reply = "谢谢你关心我，我也希望你今天顺顺利利。"
        elif intent == "question":
            reply = f"我感受到你想交流。就语气来看，你现在偏{emotion}。"
        elif intent == "complaint" and emotion in {"sad", "angry"}:
            reply = "辛苦了，我先点点头陪你，把情绪慢慢放下来。"

        if perform_song:
            intent = "sing"
            intent_score = 1.0
            led = (255, 190, 60)
            motion = "wiggle"
            reply = "好呀，我给你唱一首两只老虎。"

        return AnalysisResult(
            text=text,
            emotion=emotion,
            emotion_score=emotion_score,
            intent=intent,
            intent_score=intent_score,
            reply=reply,
            led=led,
            motion=motion,
            perform_song=perform_song,
        )

    def perform_two_tigers(self) -> None:
        performance = [
            ("两只老虎，两只老虎", (255, 120, 60), "wiggle"),
            ("跑得快，跑得快", (255, 220, 80), "wiggle"),
            ("一只没有耳朵", (80, 180, 255), "nod"),
            ("一只没有尾巴", (120, 255, 160), "nod"),
            ("真奇怪，真奇怪", (255, 90, 180), "wiggle"),
        ]

        print("\n========== Song Mode ==========")
        print("歌曲: 两只老虎")
        print("表演开始")
        print("================================\n")

        for lyric, color, motion in performance:
            if motion == "nod":
                self.hardware.nod(cycles=2, center=90, amplitude=SONG_NOD_AMPLITUDE, step_delay_ms=9)
            else:
                self.hardware.wiggle(cycles=2, center=90, amplitude=SONG_WIGGLE_AMPLITUDE, step_delay_ms=9)
            self.hardware.flash_led(color, flashes=4, flash_delay=0.12)
            self.speak_text(lyric, rate=145)
            time.sleep(0.15)

        self.hardware.set_led((255, 180, 60))
        self.hardware.wiggle(cycles=1, center=90, amplitude=42, step_delay_ms=10)
        self.speak_text("唱完啦，希望你喜欢。", rate=175)

    def respond(self, result: AnalysisResult) -> None:
        if result.perform_song:
            self.speak_text(result.reply, rate=175)
            self.perform_two_tigers()
            return

        if result.motion == "nod":
            self.hardware.nod(cycles=2, center=90, amplitude=NORMAL_NOD_AMPLITUDE, step_delay_ms=10)
        else:
            self.hardware.wiggle(cycles=2, center=90, amplitude=NORMAL_WIGGLE_AMPLITUDE, step_delay_ms=10)
        self.hardware.flash_led(result.led, flashes=3, flash_delay=0.1)

        self.speak_text(result.reply)

    def print_result(self, result: AnalysisResult) -> None:
        print("\n========== Talking Plant ==========")
        print(f"识别文本: {result.text}")
        print(f"情绪: {result.emotion} ({result.emotion_score:.3f})")
        print(f"意图: {result.intent} ({result.intent_score:.3f})")
        print(f"回复: {result.reply}")
        print(f"灯光: {result.led} | 动作: {result.motion}")
        print("===================================\n")

    def run(self):
        self.hardware.idle_pose()
        print("Talking Plant 已启动。")
        print("玩法：现在是自动对话模式，直接对着小绿植说话；按 Ctrl+C 退出。")
        self.hardware.listen_pose()
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=int(SAMPLE_RATE * BLOCK_SECONDS),
            callback=self.audio_callback,
        ):
            while self.running:
                self.update_audio_buffer()
                now = time.time()

                if self.is_speaking or now < self.cooldown_until:
                    time.sleep(0.05)
                    continue

                if now - self.last_transcribe_time < TRANSCRIBE_INTERVAL:
                    time.sleep(0.05)
                    continue

                self.last_transcribe_time = now
                text = self.transcribe_audio(self.audio_buffer)

                if not text:
                    continue

                if self.is_similar_to_last_text(text):
                    self.clear_audio_buffers()
                    continue

                self.last_text = text
                self.clear_audio_buffers()
                self.hardware.idle_pose()
                result = self.analyze_text(text)
                self.print_result(result)
                self.respond(result)
                self.cooldown_until = max(self.cooldown_until, time.time() + POST_RESPONSE_COOLDOWN)
                self.hardware.listen_pose()


if __name__ == "__main__":
    plant = TalkingPlant()
    try:
        plant.run()
    except KeyboardInterrupt:
        plant.running = False
        plant.hardware.sleep()
        print("Talking Plant 已停止。")
    finally:
        try:
            plant.hardware.sleep()
        except Exception:
            pass
        if plant.tts_engine is not None:
            try:
                plant.tts_engine.stop()
            except Exception:
                pass

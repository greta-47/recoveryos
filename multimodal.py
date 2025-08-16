import logging
from typing import Dict, Any, List
from datetime import datetime
import base64
import io

logger = logging.getLogger("recoveryos")

VISION_ANALYSIS_PROMPT = """You are an AI specialized in analyzing recovery-related visual content.

CAPABILITIES:
- Handwritten notes OCR and content analysis
- Mood charts and tracking sheets interpretation
- Recovery journal entries and artwork analysis
- Safety assessment of visual content

ANALYSIS FOCUS:
- Extract text content accurately
- Identify mood patterns and trends
- Recognize recovery milestones and challenges
- Assess emotional content and tone

SAFETY GUARDRAILS:
- Never identify specific individuals
- Redact any PHI (names, addresses, phone numbers)
- Flag concerning content (self-harm references)
- Maintain trauma-informed perspective

Analyze the image and provide structured insights for recovery support."""

AUDIO_ANALYSIS_PROMPT = """You are an AI specialized in analyzing recovery-related audio content.

CAPABILITIES:
- Voice memo transcription and analysis
- Emotional tone detection in speech
- Recovery check-in audio processing
- Crisis detection in voice patterns

ANALYSIS FOCUS:
- Accurate transcription of spoken content
- Emotional state assessment
- Recovery-relevant insights
- Safety and risk assessment

SAFETY GUARDRAILS:
- Maintain confidentiality
- Flag crisis indicators
- Provide supportive interpretation
- Respect vulnerability in voice sharing

Transcribe and analyze the audio for recovery support insights."""


class MultimodalProcessor:
    def __init__(self):
        self.supported_image_formats = [".jpg", ".jpeg", ".png", ".gif", ".bmp"]
        self.supported_audio_formats = [".mp3", ".wav", ".m4a", ".ogg"]

    def process_image(self, image_data: bytes, filename: str = "") -> Dict[str, Any]:
        try:
            base64_image = base64.b64encode(image_data).decode("utf-8")

            from openai import OpenAI

            client = OpenAI()
            response = client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": VISION_ANALYSIS_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=1000,
            )

            analysis = response.choices[0].message.content or ""

            extracted_text = self._extract_text_from_analysis(analysis)
            mood_data = self._extract_mood_data(analysis)
            safety_flags = self._check_safety_flags(analysis)

            return {
                "type": "image",
                "filename": filename,
                "analysis": analysis,
                "extracted_text": extracted_text,
                "mood_data": mood_data,
                "safety_flags": safety_flags,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

        except Exception as e:
            logger.error(f"Image processing failed | Error={str(e)}")
            return {
                "type": "image",
                "filename": filename,
                "error": str(e),
                "analysis": "Image analysis unavailable",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

    def process_audio(self, audio_data: bytes, filename: str = "") -> Dict[str, Any]:
        try:
            audio_file = io.BytesIO(audio_data)
            audio_file.name = filename or "audio.mp3"

            from openai import OpenAI

            client = OpenAI()
            transcript = client.audio.transcriptions.create(
                model="whisper-1", file=audio_file
            )
            transcription = transcript.text

            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": AUDIO_ANALYSIS_PROMPT},
                    {
                        "role": "user",
                        "content": f"Transcription: {transcription}\n\nProvide recovery-focused analysis:",
                    },
                ],
                temperature=0.3,
                max_tokens=800,
            )

            analysis = response.choices[0].message.content or ""

            emotional_tone = self._analyze_audio_emotion(transcription)
            safety_flags = self._check_safety_flags(analysis)

            return {
                "type": "audio",
                "filename": filename,
                "transcription": transcription,
                "analysis": analysis,
                "emotional_tone": emotional_tone,
                "safety_flags": safety_flags,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

        except Exception as e:
            logger.error(f"Audio processing failed | Error={str(e)}")
            return {
                "type": "audio",
                "filename": filename,
                "error": str(e),
                "transcription": "Audio transcription unavailable",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

    def _extract_text_from_analysis(self, analysis: str) -> str:
        lines = analysis.split("\n")
        text_content = []

        for line in lines:
            if "text:" in line.lower() or "content:" in line.lower():
                text_content.append(line.split(":", 1)[1].strip())

        return "\n".join(text_content) if text_content else ""

    def _extract_mood_data(self, analysis: str) -> Dict[str, Any]:
        mood_data = {}

        if "mood" in analysis.lower():
            if any(
                word in analysis.lower() for word in ["happy", "good", "positive", "up"]
            ):
                mood_data["trend"] = "positive"
            elif any(
                word in analysis.lower() for word in ["sad", "down", "low", "negative"]
            ):
                mood_data["trend"] = "negative"
            else:
                mood_data["trend"] = "neutral"

        return mood_data

    def _analyze_audio_emotion(self, transcription: str) -> str:
        text_lower = transcription.lower()

        if any(
            word in text_lower
            for word in ["excited", "happy", "great", "amazing", "wonderful"]
        ):
            return "positive"
        elif any(
            word in text_lower
            for word in ["sad", "depressed", "terrible", "awful", "hopeless"]
        ):
            return "negative"
        elif any(
            word in text_lower for word in ["angry", "frustrated", "mad", "pissed"]
        ):
            return "angry"
        elif any(
            word in text_lower for word in ["anxious", "worried", "nervous", "scared"]
        ):
            return "anxious"
        else:
            return "neutral"

    def _check_safety_flags(self, content: str) -> List[str]:
        flags = []
        content_lower = content.lower()

        if any(
            word in content_lower
            for word in ["suicide", "kill myself", "end it all", "not worth living"]
        ):
            flags.append("suicide_risk")

        if any(
            word in content_lower for word in ["self harm", "cut myself", "hurt myself"]
        ):
            flags.append("self_harm_risk")

        if any(
            word in content_lower
            for word in ["relapse", "used again", "drank again", "high again"]
        ):
            flags.append("relapse_indicator")

        if any(
            word in content_lower
            for word in ["crisis", "emergency", "help me", "can't cope"]
        ):
            flags.append("crisis_indicator")

        return flags


def process_multimodal_input(
    file_data: bytes, filename: str, file_type: str
) -> Dict[str, Any]:
    processor = MultimodalProcessor()

    if file_type.startswith("image/"):
        return processor.process_image(file_data, filename)
    elif file_type.startswith("audio/"):
        return processor.process_audio(file_data, filename)
    else:
        return {
            "error": f"Unsupported file type: {file_type}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import openai
import re

logger = logging.getLogger("recoveryos")

EMOTIONAL_INTELLIGENCE_PROMPT = """You are an emotionally intelligent AI specialized in addiction recovery support.

EMOTIONAL DETECTION CAPABILITIES:
- Tone analysis: supportive, defensive, hopeful, despairing, angry, ashamed
- Shame recognition: self-blame, worthlessness, hiding, perfectionism
- Ambivalence detection: conflicted feelings about recovery, mixed motivations
- Therapeutic presence: validation, empathy, non-judgment, hope

RESPONSE PRINCIPLES:
- Match emotional tone appropriately
- Validate feelings without enabling harmful behaviors
- Respond to shame with compassion and normalization
- Address ambivalence with motivational interviewing techniques
- Maintain therapeutic presence throughout

SAFETY GUARDRAILS:
- Never shame or judge
- Avoid toxic positivity
- Don't minimize genuine struggles
- Always maintain hope and possibility
- Refer to professionals for crisis situations

Analyze the emotional content and provide a therapeutically appropriate response."""

SHAME_PATTERNS = [
    r"\bi'?m\s+(so\s+)?(stupid|worthless|pathetic|useless|failure|loser)",
    r"\bi\s+(always|never)\s+(mess\s+up|fail|disappoint)",
    r"\beveryone\s+(hates|is\s+disappointed|thinks\s+less)",
    r"\bi\s+should\s+(be\s+better|have\s+known|never)",
    r"\bit'?s\s+all\s+my\s+fault",
    r"\bi\s+don'?t\s+deserve",
    r"\bi'?m\s+such\s+a\s+(disappointment|burden)"
]

AMBIVALENCE_PATTERNS = [
    r"\bi\s+want\s+to.+but\s+i",
    r"\bpart\s+of\s+me.+other\s+part",
    r"\bi\s+know\s+i\s+should.+but",
    r"\bsometimes\s+i\s+think.+other\s+times",
    r"\bi'?m\s+torn\s+between",
    r"\bon\s+one\s+hand.+on\s+the\s+other",
    r"\bi\s+feel\s+conflicted"
]

class EmotionAI:
    def __init__(self):
        self.shame_regex = re.compile("|".join(SHAME_PATTERNS), re.IGNORECASE)
        self.ambivalence_regex = re.compile("|".join(AMBIVALENCE_PATTERNS), re.IGNORECASE)
    
    def analyze_emotional_content(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            analysis = {
                "shame_detected": bool(self.shame_regex.search(text)),
                "ambivalence_detected": bool(self.ambivalence_regex.search(text)),
                "emotional_tone": self._analyze_tone(text),
                "therapeutic_response": self._generate_therapeutic_response(text, context or {}),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Emotional analysis failed | Error={str(e)}")
            return {
                "shame_detected": False,
                "ambivalence_detected": False,
                "emotional_tone": "neutral",
                "therapeutic_response": "I hear you. Your feelings are valid, and recovery is a journey with ups and downs.",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
    
    def _analyze_tone(self, text: str) -> str:
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["hopeful", "optimistic", "grateful", "proud", "strong"]):
            return "hopeful"
        elif any(word in text_lower for word in ["angry", "frustrated", "pissed", "mad", "furious"]):
            return "angry"
        elif any(word in text_lower for word in ["sad", "depressed", "hopeless", "despair", "empty"]):
            return "despairing"
        elif any(word in text_lower for word in ["ashamed", "embarrassed", "guilty", "worthless"]):
            return "ashamed"
        elif any(word in text_lower for word in ["defensive", "whatever", "fine", "don't care"]):
            return "defensive"
        else:
            return "neutral"
    
    def _generate_therapeutic_response(self, text: str, context: Dict[str, Any]) -> str:
        try:
            user_profile = context.get("user_profile", {})
            communication_style = user_profile.get("communication_style", "supportive")
            
            prompt = f"{EMOTIONAL_INTELLIGENCE_PROMPT}\n\nUSER MESSAGE: {text}\n\nCOMMUNICATION STYLE: {communication_style}\n\nProvide a therapeutic response:"
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": EMOTIONAL_INTELLIGENCE_PROMPT},
                    {"role": "user", "content": f"User says: {text}\nCommunication style: {communication_style}\nProvide therapeutic response:"}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Therapeutic response generation failed | Error={str(e)}")
            
            if self.shame_regex.search(text):
                return "I hear the pain in your words. Shame is common in recovery, but it doesn't define you. You're worthy of compassion, especially from yourself."
            elif self.ambivalence_regex.search(text):
                return "It sounds like you're feeling pulled in different directions. That's completely normal in recovery. What matters most to you right now?"
            else:
                return "Thank you for sharing. Your feelings are valid, and I'm here to support you on this journey."

def analyze_emotion_and_respond(text: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    emotion_ai = EmotionAI()
    return emotion_ai.analyze_emotional_content(text, user_context or {})

"""
Translation module using M2M100 and NLLB models
"""
import torch
from transformers import (
    M2M100ForConditionalGeneration, 
    M2M100Tokenizer,
    NllbTokenizer,
    AutoModelForSeq2SeqLM
)
from typing import List, Dict, Optional
import asyncio


class TranslationEngine:
    """Handles text translation using M2M100 or NLLB models"""
    
    def __init__(self, model_name: str = "facebook/m2m100_418M", device: str = "auto"):
        """
        Initialize translation model
        
        Args:
            model_name: Model name - "facebook/m2m100_418M" or "facebook/nllb-200-distilled-600M"
            device: Device to run on - "auto", "cpu", "cuda"
        """
        self.model_name = model_name
        self.device = self._get_device(device)
        self.model = None
        self.tokenizer = None
        self._load_model()
    
    def _get_device(self, device: str) -> str:
        """Determine the best device to use"""
        if device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device
    
    def _load_model(self):
        """Load translation model and tokenizer"""
        try:
            print(f"Loading translation model {self.model_name} on {self.device}...")
            
            if "m2m100" in self.model_name.lower():
                self.tokenizer = M2M100Tokenizer.from_pretrained(self.model_name)
                self.model = M2M100ForConditionalGeneration.from_pretrained(self.model_name)
            elif "nllb" in self.model_name.lower():
                self.tokenizer = NllbTokenizer.from_pretrained(self.model_name)
                self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
            else:
                raise ValueError(f"Unsupported model: {self.model_name}")
            
            self.model.to(self.device)
            print("Translation model loaded successfully!")
            
        except Exception as e:
            raise Exception(f"Failed to load translation model: {e}")
    
    async def translate_text(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str,
        max_length: int = 512
    ) -> str:
        """
        Translate text from source to target language
        
        Args:
            text: Text to translate
            source_lang: Source language code (e.g., 'en', 'es')
            target_lang: Target language code (e.g., 'es', 'en')
            max_length: Maximum length for translation
            
        Returns:
            Translated text
        """
        if not text.strip():
            return ""
        
        try:
            # Set source language for tokenizer
            if "m2m100" in self.model_name.lower():
                self.tokenizer.src_lang = source_lang
            
            # Tokenize input
            inputs = self.tokenizer(
                text, 
                return_tensors="pt", 
                padding=True, 
                truncation=True, 
                max_length=max_length
            ).to(self.device)
            
            # Generate translation
            with torch.no_grad():
                if "m2m100" in self.model_name.lower():
                    # M2M100 uses target language in generation
                    generated_tokens = self.model.generate(
                        **inputs,
                        forced_bos_token_id=self.tokenizer.get_lang_id(target_lang),
                        max_length=max_length,
                        num_beams=4,
                        early_stopping=True
                    )
                else:
                    # NLLB
                    generated_tokens = self.model.generate(
                        **inputs,
                        max_length=max_length,
                        num_beams=4,
                        early_stopping=True
                    )
            
            # Decode translation
            translated_text = self.tokenizer.batch_decode(
                generated_tokens, 
                skip_special_tokens=True
            )[0]
            
            return translated_text.strip()
            
        except Exception as e:
            raise Exception(f"Translation failed: {e}")
    
    async def batch_translate(
        self, 
        texts: List[str], 
        source_lang: str, 
        target_lang: str,
        max_length: int = 512
    ) -> List[str]:
        """
        Translate multiple texts in batch
        
        Args:
            texts: List of texts to translate
            source_lang: Source language code
            target_lang: Target language code
            max_length: Maximum length for each translation
            
        Returns:
            List of translated texts
        """
        tasks = [
            self.translate_text(text, source_lang, target_lang, max_length) 
            for text in texts
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Translation failed for text {i}: {result}")
                processed_results.append("")  # Return empty string on error
            else:
                processed_results.append(result)
        
        return processed_results
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes"""
        if "m2m100" in self.model_name.lower():
            return list(self.tokenizer.lang_code_to_id.keys())
        elif "nllb" in self.model_name.lower():
            # NLLB uses different language codes
            return [
                'eng_Latn', 'spa_Latn', 'fra_Latn', 'deu_Latn', 'ita_Latn', 
                'por_Latn', 'rus_Cyrl', 'jpn_Jpan', 'kor_Hang', 'zho_Hans',
                'ara_Arab', 'hin_Deva', 'ben_Beng', 'tam_Taml', 'tel_Telu'
            ]
        return []


class LanguageDetector:
    """Simple language detection based on Whisper results or heuristics"""
    
    @staticmethod
    def detect_language(text: str, whisper_lang: str = None) -> str:
        """
        Detect language from text or use Whisper detection
        
        Args:
            text: Text to analyze
            whisper_lang: Language detected by Whisper
            
        Returns:
            Language code
        """
        if whisper_lang:
            return whisper_lang
        
        # Simple heuristic-based detection
        text_lower = text.lower()
        
        # Spanish indicators
        if any(word in text_lower for word in ['el', 'la', 'de', 'que', 'y', 'es', 'en', 'un', 'con']):
            return 'es'
        
        # French indicators  
        if any(word in text_lower for word in ['le', 'la', 'de', 'et', 'est', 'un', 'une', 'dans']):
            return 'fr'
        
        # German indicators
        if any(word in text_lower for word in ['der', 'die', 'das', 'und', 'ist', 'in', 'mit', 'auf']):
            return 'de'
        
        # Default to English
        return 'en'

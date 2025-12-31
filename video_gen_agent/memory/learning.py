"""
Learning System - Improves video generation based on user ratings.
Analyzes patterns and adjusts agent behavior.
"""

from typing import Optional
from video_gen_agent.memory.database import VideoGenDatabase


class LearningSystem:
    """Learning system that improves from user ratings."""
    
    def __init__(self, database: Optional[VideoGenDatabase] = None):
        """Initialize the learning system."""
        self.db = database or VideoGenDatabase()
    
    def analyze_ratings(self) -> dict:
        """
        Analyze all ratings to identify patterns and areas for improvement.
        
        Returns:
            Dict with insights and recommendations
        """
        category_ratings = self.db.get_ratings_by_category()
        low_aspects = self.db.get_low_rated_aspects(threshold=3.5)
        
        insights = {
            "total_ratings": category_ratings.get("total_ratings", 0),
            "category_averages": category_ratings,
            "low_rated_aspects": low_aspects,
            "recommendations": []
        }
        
        # Generate recommendations based on patterns
        if category_ratings.get("total_ratings", 0) >= 3:
            # Need at least 3 ratings for meaningful patterns
            
            if category_ratings.get("script", 5) < 3.5:
                insights["recommendations"].append({
                    "aspect": "script",
                    "issue": "Scripts receiving lower ratings",
                    "suggestion": "Focus on more engaging hooks and clearer structure"
                })
                self.db.update_preference(
                    "script", "style", "more_engaging", 
                    confidence=0.5 + (3.5 - category_ratings["script"]) * 0.1
                )
            
            if category_ratings.get("visuals", 5) < 3.5:
                insights["recommendations"].append({
                    "aspect": "visuals",
                    "issue": "Visual selection needs improvement",
                    "suggestion": "Search for more specific, high-quality footage"
                })
                self.db.update_preference(
                    "visuals", "quality", "higher_quality",
                    confidence=0.5 + (3.5 - category_ratings["visuals"]) * 0.1
                )
            
            if category_ratings.get("audio", 5) < 3.5:
                insights["recommendations"].append({
                    "aspect": "audio",
                    "issue": "Audio/voiceover quality concerns",
                    "suggestion": "Adjust speaking speed or use different voice style"
                })
                self.db.update_preference(
                    "audio", "style", "clearer_speech",
                    confidence=0.5 + (3.5 - category_ratings["audio"]) * 0.1
                )
            
            if category_ratings.get("pacing", 5) < 3.5:
                insights["recommendations"].append({
                    "aspect": "pacing",
                    "issue": "Pacing issues detected",
                    "suggestion": "Adjust clip durations and transitions"
                })
                # Determine if too fast or too slow based on feedback analysis
                self.db.update_preference(
                    "pacing", "speed", "moderate",
                    confidence=0.5 + (3.5 - category_ratings["pacing"]) * 0.1
                )
        
        return insights
    
    def get_improvement_suggestions(self, generation_id: int) -> list[str]:
        """
        Get specific improvement suggestions for a generation.
        
        Args:
            generation_id: ID of the generation to analyze
        
        Returns:
            List of improvement suggestions
        """
        generation = self.db.get_generation(generation_id)
        if not generation:
            return ["Generation not found"]
        
        suggestions = []
        ratings = self.db.get_ratings_by_category()
        
        # Compare to averages and suggest improvements
        if ratings.get("total_ratings", 0) > 0:
            if ratings["script"] and ratings["script"] < 3.5:
                suggestions.append(
                    "Consider using stronger hooks and more varied content structure"
                )
            
            if ratings["visuals"] and ratings["visuals"] < 3.5:
                suggestions.append(
                    "Try more specific search queries for stock footage"
                )
            
            if ratings["pacing"] and ratings["pacing"] < 3.5:
                suggestions.append(
                    "Experiment with different transition durations"
                )
        
        if not suggestions:
            suggestions.append("No specific improvements identified based on current ratings")
        
        return suggestions
    
    def enhance_prompt_with_learnings(self, base_prompt: str, prompt_type: str = "general") -> str:
        """
        Enhance an agent prompt with learned preferences.
        
        Args:
            base_prompt: The original prompt
            prompt_type: Type of prompt ('script', 'visuals', 'audio', 'general')
        
        Returns:
            Enhanced prompt with learned preferences
        """
        preferences = self.db.get_preferences()
        
        if not preferences:
            return base_prompt
        
        enhancements = []
        
        for pref in preferences:
            if pref["confidence"] < 0.5:
                continue  # Skip low-confidence preferences
            
            pref_type = pref["preference_type"]
            pref_key = pref["preference_key"]
            pref_value = pref["preference_value"]
            
            # Add relevant enhancements based on preference type
            if pref_type == "script" and prompt_type in ["script", "general"]:
                if pref_value == "more_engaging":
                    enhancements.append("Focus on creating highly engaging, hook-driven content")
            
            elif pref_type == "visuals" and prompt_type in ["visuals", "general"]:
                if pref_value == "higher_quality":
                    enhancements.append("Prioritize high-quality, professional-looking footage")
            
            elif pref_type == "audio" and prompt_type in ["audio", "general"]:
                if pref_value == "clearer_speech":
                    enhancements.append("Ensure clear, well-paced narration")
            
            elif pref_type == "pacing" and prompt_type in ["pacing", "general"]:
                if pref_value == "moderate":
                    enhancements.append("Use moderate pacing with smooth transitions")
        
        if enhancements:
            enhancement_text = "\n\nLEARNED PREFERENCES (apply these based on past feedback):\n"
            enhancement_text += "\n".join(f"- {e}" for e in enhancements)
            return base_prompt + enhancement_text
        
        return base_prompt
    
    def get_learning_summary(self) -> dict:
        """
        Get a summary of what the system has learned.
        
        Returns:
            Summary dict with learned patterns
        """
        insights = self.analyze_ratings()
        preferences = self.db.get_preferences()
        
        summary = {
            "total_generations_rated": insights["total_ratings"],
            "category_performance": {},
            "learned_preferences": [],
            "improvement_areas": []
        }
        
        # Category performance
        for category in ["script", "visuals", "audio", "pacing"]:
            avg = insights["category_averages"].get(category)
            if avg:
                summary["category_performance"][category] = {
                    "average": round(avg, 2),
                    "status": "good" if avg >= 3.5 else "needs_improvement"
                }
        
        # Learned preferences
        for pref in preferences:
            if pref["confidence"] >= 0.5:
                summary["learned_preferences"].append({
                    "type": pref["preference_type"],
                    "preference": f"{pref['preference_key']}: {pref['preference_value']}",
                    "confidence": round(pref["confidence"], 2)
                })
        
        # Areas needing improvement
        summary["improvement_areas"] = [
            aspect["aspect"] for aspect in insights["low_rated_aspects"]
        ]
        
        return summary

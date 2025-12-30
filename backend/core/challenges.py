import json
import random
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, date


def pick_challenge(target_facets: List[str], team_context: Optional[str] = None) -> Dict[str, Any]:
    """
    Pick a challenge from templates based on target facets.
    Returns challenge template or creates a simple fallback.
    """
    path = Path("data/challenge_templates.json")
    templates = []
    
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                templates = json.load(f)
        except Exception:
            pass
    
    if not templates:
        # Fallback challenges
        templates = [
            {
                "title": "Daily Mindfulness Check-ins",
                "target_facets": ["self_awareness"],
                "daily_tasks": [
                    "Take 3 deep breaths and notice one emotion",
                    "Identify one trigger from yesterday",
                    "Name one physical sensation you feel right now",
                    "Observe one thought pattern without judgment",
                    "Notice one thing you're grateful for",
                    "Reflect on one interaction that went well",
                    "Set one small intention for tomorrow"
                ],
                "description": "Build self-awareness through daily mindful observations"
            },
            {
                "title": "Regulation Response Challenge",
                "target_facets": ["self_regulation"],
                "daily_tasks": [
                    "Practice box breathing for 2 minutes",
                    "Use the 5-4-3-2-1 grounding technique",
                    "Take a 30-second pause before responding to stress",
                    "Practice progressive muscle relaxation",
                    "Do a 2-minute walking meditation",
                    "Try the 'STOP' technique when triggered",
                    "End the day with 3 calming breaths"
                ],
                "description": "Strengthen emotional regulation through daily practices"
            },
            {
                "title": "Connection & Empathy Week",
                "target_facets": ["empathy", "social_skills"],
                "daily_tasks": [
                    "Ask one person 'How are you really doing?'",
                    "Practice active listening in one conversation",
                    "Express appreciation to someone on your team",
                    "Consider another person's perspective in a conflict",
                    "Offer help to a colleague without being asked",
                    "Share something meaningful with a friend",
                    "Reflect on how your actions affected others today"
                ],
                "description": "Deepen connections and empathy through daily interactions"
            },
            {
                "title": "Motivation Momentum Builder",
                "target_facets": ["motivation"],
                "daily_tasks": [
                    "Identify one small win from yesterday",
                    "Set one achievable goal for today",
                    "Take one step toward a larger objective",
                    "Celebrate progress on a project",
                    "Connect today's work to your bigger purpose",
                    "Share your progress with someone supportive",
                    "Plan one thing you're excited about tomorrow"
                ],
                "description": "Build and maintain motivation through daily momentum"
            }
        ]
    
    # Filter by target facets if provided
    if target_facets:
        matching_templates = []
        for template in templates:
            template_facets = template.get("target_facets", [])
            if any(facet in template_facets for facet in target_facets):
                matching_templates.append(template)
        
        if matching_templates:
            templates = matching_templates
    
    # Pick random template
    chosen = random.choice(templates)
    
    # Add team context if provided
    if team_context:
        chosen = chosen.copy()
        chosen["team_context"] = team_context
    
    return chosen


def update_streak(prev_state: Dict[str, Any], completed_today: bool) -> Dict[str, Any]:
    """
    Update streak based on completion status.
    prev_state: {streak: int, days_completed: List[str], last_completed: str}
    Returns updated state.
    """
    today_str = date.today().isoformat()
    
    # Initialize if no previous state
    if not prev_state:
        prev_state = {
            "streak": 0,
            "days_completed": [],
            "last_completed": None
        }
    
    current_streak = prev_state.get("streak", 0)
    days_completed = prev_state.get("days_completed", []).copy()
    last_completed = prev_state.get("last_completed")
    
    if completed_today:
        # Add today to completed days if not already there
        if today_str not in days_completed:
            days_completed.append(today_str)
        
        # Update streak logic
        if last_completed:
            last_date = datetime.fromisoformat(last_completed).date()
            today_date = date.today()
            days_diff = (today_date - last_date).days
            
            if days_diff == 1:  # Consecutive day
                current_streak += 1
            elif days_diff == 0:  # Same day (already completed)
                pass  # No change to streak
            else:  # Gap in completion
                current_streak = 1  # Reset to 1 for today
        else:
            current_streak = 1  # First completion
        
        last_completed = today_str
    
    return {
        "streak": current_streak,
        "days_completed": sorted(list(set(days_completed))),  # Remove duplicates and sort
        "last_completed": last_completed
    }


def get_leaderboard_data(participations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort participations by streak and days completed for leaderboard.
    Only includes safe data (no sentiment/journal content).
    """
    def sort_key(p: Dict[str, Any]) -> tuple:
        streak = p.get("streak", 0)
        days_count = len(p.get("days_completed", []))
        return (-streak, -days_count)  # Descending order
    
    # Sort and return only safe fields
    sorted_participations = sorted(participations, key=sort_key)
    
    leaderboard = []
    for p in sorted_participations:
        entry = {
            "user_id": p.get("user_id"),
            "challenge_id": p.get("challenge_id"),
            "streak": p.get("streak", 0),
            "days_completed_count": len(p.get("days_completed", [])),
            "last_completed": p.get("last_completed")
        }
        leaderboard.append(entry)
    
    return leaderboard


def generate_challenge_from_rag(target_facets: List[str], team_context: str, llm=None) -> Optional[Dict[str, Any]]:
    """
    Optional: Generate challenge using RAG/LLM if available.
    Falls back to pick_challenge if LLM unavailable.
    """
    if llm is None:
        return pick_challenge(target_facets, team_context)
    
    try:
        from prompts.prompt_lib import PROMPT_REGISTRY
        
        prompt = PROMPT_REGISTRY.get("challenge_generator")
        if not prompt:
            return pick_challenge(target_facets, team_context)
        
        messages = prompt.format_messages(
            target_facets=target_facets,
            team_context=team_context or "general team"
        )
        
        resp = llm.invoke(messages)
        raw = getattr(resp, "content", None) or str(resp)
        
        # Try to parse JSON response
        import json
        challenge_data = json.loads(raw)
        
        # Validate required fields
        required = ["title", "daily_tasks"]
        if all(key in challenge_data for key in required):
            return challenge_data
        
    except Exception:
        pass
    
    # Fall back to template-based selection
    return pick_challenge(target_facets, team_context)
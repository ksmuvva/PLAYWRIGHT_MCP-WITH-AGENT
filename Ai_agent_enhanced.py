#!/usr/bin/env python3

import asyncio
import json
import logging
import sys
import argparse
from typing import Optional, Dict, Any, List, Union
import os
import time
from datetime import datetime
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import all tool classes
from Tools.AdvancedBrowser.advanced import AdvancedBrowserTools
from Tools.BrowserControl.navigation import BrowserControlTools
from Tools.ContentExtraction.extraction import ContentExtractionTools
from Tools.ElementInteraction.interaction import ElementInteractionTools
from Tools.ElementLocation.location import ElementLocationTools
from Tools.Network.network import NetworkTools
from Tools.Debug.debug import DebugTools
from mcp_client import MCPToolClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ToolExecutionResult:
    """Detailed result of tool execution with validation and feedback"""
    tool_name: str
    success: bool
    result_data: Any = None
    execution_time: float = 0.0
    error_message: str = ""
    screenshot_before: str = ""
    screenshot_after: str = ""
    validation_results: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    suggestions: List[str] = field(default_factory=list)
    context_before: Dict[str, Any] = field(default_factory=dict)
    context_after: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "result_data": str(self.result_data) if self.result_data else "",
            "execution_time": self.execution_time,
            "error_message": self.error_message,
            "screenshot_before": self.screenshot_before,
            "screenshot_after": self.screenshot_after,
            "validation_results": self.validation_results,
            "retry_count": self.retry_count,
            "suggestions": self.suggestions,
            "context_before": self.context_before,
            "context_after": self.context_after,
            "timestamp": self.timestamp
        }

class ResultValidator:
    """Validates tool execution results and provides feedback"""
    
    def __init__(self, browser_tools):
        self.browser_tools = browser_tools
    
    async def validate_navigation(self, result: ToolExecutionResult, url: str) -> Dict[str, Any]:
        """Validate navigation results"""
        validation = {
            "url_loaded": False,
            "page_title": "",
            "page_ready": False,
            "error_on_page": False
        }
        
        try:
            # Get current page info
            page_info = await self.browser_tools.playwright_get_page_info()
            if isinstance(page_info, dict):
                validation["url_loaded"] = url.lower() in page_info.get("url", "").lower()
                validation["page_title"] = page_info.get("title", "")
                validation["page_ready"] = page_info.get("ready_state") == "complete"
            
            # Check for JavaScript errors
            console_logs = await self.browser_tools.playwright_get_console_logs()
            if isinstance(console_logs, list):
                validation["error_on_page"] = any(
                    log.get("type") == "error" for log in console_logs[-5:]  # Check last 5 logs
                )
                
        except Exception as e:
            validation["validation_error"] = str(e)
        
        return validation
    
    async def validate_element_interaction(self, result: ToolExecutionResult, selector: str) -> Dict[str, Any]:
        """Validate element interaction results"""
        validation = {
            "element_exists": False,
            "element_visible": False,
            "element_enabled": False,
            "element_changed": False
        }
        
        try:
            # Check if element exists and is interactive
            element_info = await self.browser_tools.playwright_element_info(selector)
            if isinstance(element_info, dict) and "error" not in element_info:
                validation["element_exists"] = True
                validation["element_visible"] = element_info.get("visible", False)
                validation["element_enabled"] = element_info.get("enabled", False)
            
            # Compare before/after context if available
            if result.context_before and result.context_after:
                validation["element_changed"] = result.context_before != result.context_after
                
        except Exception as e:
            validation["validation_error"] = str(e)
        
        return validation
    
    async def validate_content_extraction(self, result: ToolExecutionResult, selector: str = None) -> Dict[str, Any]:
        """Validate content extraction results"""
        validation = {
            "content_found": False,
            "content_length": 0,
            "is_meaningful": False
        }
        
        try:
            if result.result_data:
                content = str(result.result_data)
                validation["content_found"] = bool(content.strip())
                validation["content_length"] = len(content.strip())
                validation["is_meaningful"] = len(content.strip()) > 5  # Basic meaningfulness check
                
        except Exception as e:
            validation["validation_error"] = str(e)
        
        return validation

class FeedbackGenerator:
    """Generates intelligent feedback for the LLM based on execution results"""
    
    def __init__(self):
        self.execution_history = []
    
    def analyze_execution_results(self, results: List[ToolExecutionResult]) -> Dict[str, Any]:
        """Analyze multiple tool execution results"""
        analysis = {
            "total_tools": len(results),
            "successful": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
            "total_execution_time": sum(r.execution_time for r in results),
            "retry_count": sum(r.retry_count for r in results),
            "common_errors": self._identify_common_errors(results),
            "success_rate": 0.0,
            "performance_issues": []
        }
        
        if analysis["total_tools"] > 0:
            analysis["success_rate"] = analysis["successful"] / analysis["total_tools"]
        
        # Identify performance issues
        slow_tools = [r for r in results if r.execution_time > 5.0]
        if slow_tools:
            analysis["performance_issues"].append(f"{len(slow_tools)} tools took longer than 5 seconds")
        
        return analysis
    
    def _identify_common_errors(self, results: List[ToolExecutionResult]) -> List[str]:
        """Identify common error patterns"""
        error_patterns = []
        failed_results = [r for r in results if not r.success]
        
        if not failed_results:
            return error_patterns
        
        # Common error categories
        timeout_errors = [r for r in failed_results if "timeout" in r.error_message.lower()]
        element_errors = [r for r in failed_results if any(keyword in r.error_message.lower() 
                         for keyword in ["element", "selector", "not found"])]
        network_errors = [r for r in failed_results if any(keyword in r.error_message.lower() 
                         for keyword in ["network", "connection", "fetch"])]
        browser_errors = [r for r in failed_results if any(keyword in r.error_message.lower() 
                         for keyword in ["browser", "context", "closed"])]
        
        if timeout_errors:
            error_patterns.append(f"Timeout issues in {len(timeout_errors)} tools")
        if element_errors:
            error_patterns.append(f"Element selection issues in {len(element_errors)} tools")
        if network_errors:
            error_patterns.append(f"Network issues in {len(network_errors)} tools")
        if browser_errors:
            error_patterns.append(f"Browser state issues in {len(browser_errors)} tools")
        
        return error_patterns
    
    def generate_llm_feedback(self, results: List[ToolExecutionResult]) -> str:
        """Generate comprehensive feedback for the LLM"""
        analysis = self.analyze_execution_results(results)
        
        feedback_parts = []
        
        # Overall summary
        feedback_parts.append(f"📊 EXECUTION SUMMARY:")
        feedback_parts.append(f"   Tools executed: {analysis['total_tools']}")
        feedback_parts.append(f"   Success rate: {analysis['success_rate']:.1%}")
        feedback_parts.append(f"   Total time: {analysis['total_execution_time']:.2f}s")
        
        if analysis['failed'] > 0:
            feedback_parts.append(f"   Failed tools: {analysis['failed']}")
        
        # Detailed results
        feedback_parts.append(f"\n📋 DETAILED RESULTS:")
        for i, result in enumerate(results, 1):
            status_icon = "✅" if result.success else "❌"
            feedback_parts.append(f"   {i}. {status_icon} {result.tool_name} ({result.execution_time:.2f}s)")
            
            if not result.success:
                feedback_parts.append(f"      Error: {result.error_message}")
                if result.suggestions:
                    feedback_parts.append(f"      Suggestions: {', '.join(result.suggestions[:2])}")
            elif result.validation_results:
                # Show key validation info for successful tools
                key_validations = []
                for key, value in result.validation_results.items():
                    if isinstance(value, bool) and value:
                        key_validations.append(key)
                if key_validations:
                    feedback_parts.append(f"      Validated: {', '.join(key_validations[:3])}")
        
        # Common issues and recommendations
        if analysis['common_errors']:
            feedback_parts.append(f"\n⚠️  COMMON ISSUES:")
            for error in analysis['common_errors']:
                feedback_parts.append(f"   - {error}")
        
        # Performance insights
        if analysis['performance_issues']:
            feedback_parts.append(f"\n⏱️  PERFORMANCE:")
            for issue in analysis['performance_issues']:
                feedback_parts.append(f"   - {issue}")
        
        # Next steps recommendations
        recommendations = self._generate_recommendations(results, analysis)
        if recommendations:
            feedback_parts.append(f"\n💡 RECOMMENDATIONS:")
            for rec in recommendations[:3]:  # Limit to top 3
                feedback_parts.append(f"   - {rec}")
        
        return "\n".join(feedback_parts)
    
    def _generate_recommendations(self, results: List[ToolExecutionResult], analysis: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on results"""
        recommendations = []
        
        # If there were failures, suggest improvements
        failed_results = [r for r in results if not r.success]
        
        for result in failed_results:
            if "timeout" in result.error_message.lower():
                recommendations.append("Increase timeout values or add explicit waits")
            elif "element" in result.error_message.lower() or "selector" in result.error_message.lower():
                recommendations.append("Use more robust selectors or wait for element visibility")
            elif "browser" in result.error_message.lower():
                recommendations.append("Add browser state validation before tool execution")
        
        # Performance recommendations
        if analysis['total_execution_time'] > 15:
            recommendations.append("Consider optimizing tool sequence for better performance")
        
        # Success pattern recommendations
        if analysis['success_rate'] > 0.8:
            recommendations.append("Good execution pattern - continue with similar approach")
        elif analysis['success_rate'] < 0.5:
            recommendations.append("Consider breaking down complex tasks into smaller steps")
        
        return list(set(recommendations))  # Remove duplicates

@dataclass
class ToolExecutionFeedback:
    """Feedback data for individual tool execution sent to LLM"""
    tool_result: ToolExecutionResult
    assertion_status: str = "PENDING"  # "PASS" / "FAIL" / "RETRY" / "PENDING"
    llm_feedback: str = ""
    next_action_suggestion: str = ""
    confidence_score: float = 0.0
    should_continue: bool = True
    alternative_tools: List[str] = field(default_factory=list)
    modification_requests: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "tool_result": self.tool_result.to_dict(),
            "assertion_status": self.assertion_status,
            "llm_feedback": self.llm_feedback,
            "next_action_suggestion": self.next_action_suggestion,
            "confidence_score": self.confidence_score,
            "should_continue": self.should_continue,
            "alternative_tools": self.alternative_tools,
            "modification_requests": self.modification_requests
        }

class RealTimeFeedbackLoop:
    """Manages real-time feedback between tool execution and LLM"""
    
    def __init__(self, llm_provider, browser_tools):
        self.llm_provider = llm_provider
        self.browser_tools = browser_tools
        self.execution_history = []
        self.assertion_log = []
        self.confidence_threshold = 0.7
        
    async def send_tool_result_to_llm(self, tool_feedback: ToolExecutionFeedback, 
                                    remaining_tools: List[Dict], context: Dict[str, Any]) -> Dict[str, Any]:
        """Send individual tool result to LLM for feedback and next action decision"""
        
        # Create feedback message for LLM
        feedback_message = self._format_tool_result_for_llm(tool_feedback, remaining_tools, context)
        
        # Send to LLM and get response
        llm_response = await self._communicate_with_llm(feedback_message)
        
        # Parse LLM response
        parsed_response = self._parse_llm_feedback_response(llm_response)
        
        # Update tool feedback with LLM response
        tool_feedback.llm_feedback = parsed_response.get("assessment", "")
        tool_feedback.assertion_status = parsed_response.get("assertion", "PENDING")
        tool_feedback.next_action_suggestion = parsed_response.get("next_action", "CONTINUE")
        tool_feedback.confidence_score = parsed_response.get("confidence", 0.5)
        tool_feedback.should_continue = parsed_response.get("should_continue", True)
        tool_feedback.alternative_tools = parsed_response.get("alternative_tools", [])
        tool_feedback.modification_requests = parsed_response.get("modifications", [])
        
        # Log assertion
        self._log_assertion(tool_feedback)
        
        return parsed_response
    
    def _format_tool_result_for_llm(self, tool_feedback: ToolExecutionFeedback, 
                                  remaining_tools: List[Dict], context: Dict[str, Any]) -> str:
        """Format tool execution result for LLM consumption"""
        
        result = tool_feedback.tool_result
        
        # Create status summary
        status = "SUCCESS" if result.success else "FAILURE"
        validation_summary = ""
        if result.validation_results:
            passed_validations = [k for k, v in result.validation_results.items() if v is True]
            failed_validations = [k for k, v in result.validation_results.items() if v is False]
            validation_summary = f"Passed: {passed_validations}, Failed: {failed_validations}"
        
        # Format remaining tools
        remaining_tool_names = [tool.get("tool", "unknown") for tool in remaining_tools]
        
        feedback_json = {
            "execution_update": {
                "tool_executed": result.tool_name,
                "status": status,
                "result_data": str(result.result_data) if result.result_data else "",
                "execution_time": round(result.execution_time, 2),
                "error_message": result.error_message if not result.success else "",
                "validation": validation_summary,
                "suggestions": result.suggestions,
                "screenshots": [result.screenshot_before, result.screenshot_after] if result.screenshot_before else [],
                "remaining_tools": remaining_tool_names,
                "context": context,
                "retry_count": result.retry_count
            },
            "question": self._generate_feedback_question(result, remaining_tools)
        }
        
        return f"""TOOL EXECUTION FEEDBACK:

{json.dumps(feedback_json, indent=2)}

Please respond with your assessment and next action decision in this JSON format:
{{
  "assessment": "Brief evaluation of the tool execution result",
  "assertion": "PASS|FAIL|RETRY",
  "next_action": "CONTINUE|MODIFY|STOP|RETRY",
  "reasoning": "Explanation of your decision",
  "confidence": 0.95,
  "should_continue": true,
  "modifications": ["list of any modifications needed"],
  "alternative_tools": ["alternative tool suggestions if current failed"]
}}"""
    
    def _generate_feedback_question(self, result: ToolExecutionResult, remaining_tools: List[Dict]) -> str:
        """Generate contextual question for LLM based on execution result"""
        
        if result.success:
            if remaining_tools:
                return f"Tool '{result.tool_name}' completed successfully. Should I proceed with the next planned tool '{remaining_tools[0].get('tool', 'unknown')}' or modify the approach?"
            else:
                return f"Tool '{result.tool_name}' completed successfully and this was the final tool. Should I consider any additional actions?"
        else:
            if remaining_tools:
                return f"Tool '{result.tool_name}' failed with error: {result.error_message}. Should I retry with modifications, try an alternative approach, or skip to the next tool?"
            else:
                return f"Tool '{result.tool_name}' failed with error: {result.error_message}. This was the final tool. Should I retry with a different approach or consider the task incomplete?"
    
    async def _communicate_with_llm(self, message: str) -> str:
        """Send message to LLM and get response"""
        
        # Create conversation messages
        messages = [
            {
                "role": "system", 
                "content": self._create_feedback_system_message()
            },
            {
                "role": "user",
                "content": message
            }
        ]
        
        # Get LLM response
        response = await self.llm_provider.generate_response(messages)
        return response
    
    def _create_feedback_system_message(self) -> str:
        """Create system message for real-time feedback mode"""
        return """You are an AI Browser Automation Agent in REAL-TIME FEEDBACK MODE.

You receive individual tool execution results and must provide immediate feedback and decisions for the next action.

Your role:
1. ASSESS each tool execution result (SUCCESS/FAILURE)
2. ASSERT the outcome (PASS/FAIL/RETRY)
3. DECIDE the next action (CONTINUE/MODIFY/STOP/RETRY)
4. SUGGEST modifications or alternatives if needed

Response format (JSON only):
{
  "assessment": "Brief evaluation",
  "assertion": "PASS|FAIL|RETRY", 
  "next_action": "CONTINUE|MODIFY|STOP|RETRY",
  "reasoning": "Your decision logic",
  "confidence": 0.95,
  "should_continue": true,
  "modifications": ["specific changes needed"],
  "alternative_tools": ["alternative tools if current failed"]
}

Decision Guidelines:
- PASS: Tool succeeded, validation passed, continue as planned
- FAIL: Tool failed critically, cannot recover, stop or try alternative
- RETRY: Tool failed but recoverable, retry with modifications
- CONTINUE: Proceed with next planned tool
- MODIFY: Change parameters/approach for next tool
- STOP: Critical failure, abort execution
- Confidence: 0.0-1.0 (how confident you are in the result)

Always respond with valid JSON only."""
    
    def _parse_llm_feedback_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM feedback response"""
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                logger.warning("No JSON found in LLM feedback response")
                return self._default_feedback_response()
            
            json_str = response[json_start:json_end]
            parsed = json.loads(json_str)
            
            # Validate required fields
            required_fields = ["assessment", "assertion", "next_action", "confidence"]
            for field in required_fields:
                if field not in parsed:
                    parsed[field] = self._get_default_value(field)
            
            # Ensure confidence is between 0 and 1
            parsed["confidence"] = max(0.0, min(1.0, float(parsed.get("confidence", 0.5))))
            
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM feedback response: {e}")
            return self._default_feedback_response()
        except Exception as e:
            logger.error(f"Error processing LLM feedback: {e}")
            return self._default_feedback_response()
    
    def _default_feedback_response(self) -> Dict[str, Any]:
        """Default feedback response when parsing fails"""
        return {
            "assessment": "Unable to parse LLM response",
            "assertion": "FAIL",
            "next_action": "STOP",
            "reasoning": "LLM response parsing failed",
            "confidence": 0.1,
            "should_continue": False,
            "modifications": [],
            "alternative_tools": []
        }
    
    def _get_default_value(self, field: str) -> Any:
        """Get default value for missing fields"""
        defaults = {
            "assessment": "No assessment provided",
            "assertion": "PENDING",
            "next_action": "CONTINUE",
            "reasoning": "No reasoning provided",
            "confidence": 0.5,
            "should_continue": True,
            "modifications": [],
            "alternative_tools": []
        }
        return defaults.get(field, "")
    
    def _log_assertion(self, tool_feedback: ToolExecutionFeedback):
        """Log assertion for tracking"""
        assertion_entry = {
            "timestamp": tool_feedback.tool_result.timestamp,
            "tool_name": tool_feedback.tool_result.tool_name,
            "assertion": tool_feedback.assertion_status,
            "success": tool_feedback.tool_result.success,
            "confidence": tool_feedback.confidence_score,
            "llm_feedback": tool_feedback.llm_feedback
        }
        self.assertion_log.append(assertion_entry)
        
        # Keep only last 50 assertions
        self.assertion_log = self.assertion_log[-50:]
    
    def get_assertion_summary(self) -> Dict[str, Any]:
        """Get summary of all assertions"""
        if not self.assertion_log:
            return {"total": 0, "pass": 0, "fail": 0, "retry": 0, "success_rate": 0.0}
        
        total = len(self.assertion_log)
        pass_count = sum(1 for entry in self.assertion_log if entry["assertion"] == "PASS")
        fail_count = sum(1 for entry in self.assertion_log if entry["assertion"] == "FAIL")
        retry_count = sum(1 for entry in self.assertion_log if entry["assertion"] == "RETRY")
        
        return {
            "total": total,
            "pass": pass_count,
            "fail": fail_count,
            "retry": retry_count,
            "success_rate": pass_count / total if total > 0 else 0.0,
            "average_confidence": sum(entry["confidence"] for entry in self.assertion_log) / total if total > 0 else 0.0
        }

class LLMProvider:
    """Abstract base class for LLM providers"""
    
    def __init__(self):
        self.provider_name = "base"
    
    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        raise NotImplementedError

class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider"""
    
    def __init__(self):
        super().__init__()
        self.provider_name = "openai"
        try:
            import openai
            self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.model = os.getenv("LLM_MODEL", "gpt-4")
        except ImportError:
            raise ImportError("Please install openai: pip install openai")
    
    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        try:
            # Some newer models (e.g., GPT-5 preview) require max_completion_tokens instead of max_tokens
            params = {
                "model": self.model,
                "messages": messages,
            }
            model_lower = (self.model or "").lower()
            is_newer_model = any(flag in model_lower for flag in ["gpt-5", "o4", "omni"])
            if is_newer_model:
                params["max_completion_tokens"] = 4000  # Increased for complex tasks
            else:
                params["max_tokens"] = 4000  # Increased for complex tasks
                params["temperature"] = 0.3

            logger.info(f"Sending request to OpenAI with model: {self.model}")
            response = self.client.chat.completions.create(**params)
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            
            if not content:
                logger.warning(f"OpenAI returned empty content. Response: {response}")
                return "I apologize, but I didn't receive a response from the AI model. Please try again."
            
            if finish_reason == 'length':
                logger.warning(f"OpenAI response was truncated due to token limit. Finish reason: {finish_reason}")
                # Try to find if there's a partial JSON that we can work with
                if '{' in content and '}' in content:
                    logger.info("Found partial JSON in truncated response, attempting to use it")
                else:
                    logger.warning("No usable JSON found in truncated response")
                    return "The AI response was too long and got truncated. Please try a simpler request or break it into smaller tasks."
            
            logger.info(f"OpenAI response length: {len(content)} characters, finish_reason: {finish_reason}")
            return content
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise Exception(f"OpenAI API error: {str(e)}")

class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider"""
    
    def __init__(self):
        super().__init__()
        self.provider_name = "anthropic"
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            self.model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        except ImportError:
            raise ImportError("Please install anthropic: pip install anthropic")
    
    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        try:
            # Convert messages format for Claude
            system_msg = None
            user_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                else:
                    user_messages.append(msg)
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.3,
                system=system_msg if system_msg else "You are a helpful assistant.",
                messages=user_messages
            )
            return response.content[0].text
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")

class GeminiProvider(LLMProvider):
    """Google Gemini provider"""
    
    def __init__(self):
        super().__init__()
        self.provider_name = "gemini"
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            self.model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-1.5-pro"))
        except ImportError:
            raise ImportError("Please install google-generativeai: pip install google-generativeai")
    
    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        try:
            # Convert messages to Gemini format
            conversation_text = "\\n".join([
                f"{msg['role'].upper()}: {msg['content']}" 
                for msg in messages
            ])
            
            response = self.model.generate_content(conversation_text)
            return response.text
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")

class DirectBrowserTools(
    AdvancedBrowserTools,
    BrowserControlTools,
    ContentExtractionTools,
    ElementInteractionTools,
    ElementLocationTools,
    NetworkTools,
    DebugTools
):
    """Combined browser tools class"""
    
    def __init__(self, browser_type: str = "chromium"):
        # Normalize browser type mapping
        browser_type = self._normalize_browser_type(browser_type)
        
        # Initialize all parent classes with browser_type
        AdvancedBrowserTools.__init__(self, browser_type)
        BrowserControlTools.__init__(self, browser_type)
        ContentExtractionTools.__init__(self, browser_type)
        ElementInteractionTools.__init__(self, browser_type)
        ElementLocationTools.__init__(self, browser_type)
        NetworkTools.__init__(self, browser_type)
        DebugTools.__init__(self, browser_type)
        
        self.browser_type = browser_type.lower()
        self.available_methods = []
        self._scan_available_methods()
    
    def _normalize_browser_type(self, browser_type: str) -> str:
        """Normalize browser type names to ensure consistency"""
        browser_type = browser_type.lower().strip()
        
        # Handle Edge variations
        if browser_type in ["edge", "microsoft edge", "msedge"]:
            return "msedge"
        
        # Handle Chrome variations  
        if browser_type in ["google chrome"]:
            return "chrome"
            
        # Standard browsers
        if browser_type in ["chromium", "firefox", "webkit", "chrome"]:
            return browser_type
            
        # Default fallback
        logger.warning(f"Unknown browser type '{browser_type}', defaulting to chromium")
        return "chromium"
    
    def _scan_available_methods(self):
        """Scan for available methods from all parent classes"""
        import inspect
        
        seen_methods = set()  # Track method names to avoid duplicates
        
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if (not name.startswith('_') and 
                name not in ['initialize', 'cleanup', 'cleanup_all'] and
                name not in seen_methods and  # Avoid duplicates
                callable(method)):
                
                doc = method.__doc__ or "No description available"
                self.available_methods.append({
                    'name': name,
                    'description': doc.split('\\n')[0].strip() if doc else "No description",
                    'method': method
                })
                seen_methods.add(name)  # Mark as seen

class AIBrowserAgent:
    """Direct AI Browser Agent without MCP server"""
    
    def __init__(self, llm_provider_name: str = None, browser_type: str = "chromium", use_mcp: bool = False):
        self.llm_provider = self._initialize_llm_provider(llm_provider_name)
        self.browser_type = browser_type
        self.use_mcp = use_mcp
        
        # Only create DirectBrowserTools if not using MCP
        if not use_mcp:
            self.browser_tools = DirectBrowserTools(browser_type)
        else:
            self.browser_tools = None  # Will use MCP client instead
            
        self.conversation_history = []
        self.initialized = False
        self.mcp_client: MCPToolClient | None = None
        
        # Feedback system components
        self.result_validator = None
        self.feedback_generator = FeedbackGenerator()
        self.real_time_feedback_loop = None
        self.execution_results = []  # Store recent execution results
        self.last_feedback = ""  # Store last feedback for LLM context
        self.real_time_mode = False  # Toggle for real-time vs batch execution
    
    def _initialize_llm_provider(self, provider_name: str = None) -> LLMProvider:
        """Initialize the appropriate LLM provider"""
        if not provider_name:
            provider_name = os.getenv("LLM_PROVIDER", "openai").lower()
        
        provider_name = provider_name.lower()
        
        try:
            if provider_name == "openai":
                return OpenAIProvider()
            elif provider_name == "anthropic":
                return AnthropicProvider()
            elif provider_name == "gemini":
                return GeminiProvider()
            else:
                logger.warning(f"Unknown LLM provider '{provider_name}', defaulting to OpenAI")
                return OpenAIProvider()
        except ImportError as e:
            logger.error(f"Failed to initialize {provider_name}: {e}")
            raise Exception(f"LLM provider '{provider_name}' not available: {e}")
    
    async def initialize(self):
        """Initialize the browser tools"""
        try:
            logger.info(f"Initializing AI Browser Agent with {self.llm_provider.provider_name.upper()} and {self.browser_type.title()} browser...")
            
            if self.use_mcp:
                # MCP mode: Only start MCP client, don't initialize local browser
                self.mcp_client = MCPToolClient(browser_type=self.browser_type)
                await self.mcp_client.start_server()
                # Don't initialize local browser tools in MCP mode
            else:
                # Local mode: Initialize local browser tools
                await self.browser_tools.initialize()
            
            # Initialize feedback system components (works with both MCP and local)
            if not self.use_mcp:
                self.result_validator = ResultValidator(self.browser_tools)
                self.real_time_feedback_loop = RealTimeFeedbackLoop(self.llm_provider, self.browser_tools)
            else:
                # For MCP mode, we'll handle validation differently
                self.result_validator = None
                self.real_time_feedback_loop = None
            
            self.initialized = True
            tool_count = len(self.browser_tools.available_methods) if not self.use_mcp else "49"
            logger.info(f"AI Browser Agent initialized successfully with {tool_count} tools!")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            return False
    
    def create_system_message(self) -> str:
        """Create system message with available tools and execution feedback"""
        if self.use_mcp:
            # In MCP mode, provide a general tool description
            tools_description = """Available tools via MCP:
- playwright_navigate: Navigate to URLs
- playwright_fill: Fill form fields (use 'text' parameter, NOT 'value')
- playwright_click: Click elements
- playwright_wait_for_element: Wait for elements to appear
- playwright_get_visible_text: Extract text from elements
- playwright_check_element: Check element properties
- And 43 more browser automation tools..."""
        else:
            # Local mode: Use actual tool descriptions
            tools_description = "\\n".join([
                f"- {tool['name']}: {tool['description']}"
                for tool in self.browser_tools.available_methods[:25]  # Show first 25 tools
            ])
        
        # Include recent execution feedback if available
        feedback_section = ""
        if self.last_feedback:
            feedback_section = f"""

🔍 RECENT EXECUTION FEEDBACK:
{self.last_feedback}

Use this feedback to improve your next actions. Pay attention to:
- Failed tools and their error messages
- Suggested alternatives and improvements
- Performance insights and timing issues
- Validation results from previous executions
"""

        return f"""You are an AI Browser Automation Agent with advanced execution feedback capabilities. You can control a browser using these tools:

{tools_description}
{"... and 24 more tools." if self.use_mcp else f"... and {len(self.browser_tools.available_methods) - 25} more tools."}

EXECUTION FEEDBACK SYSTEM:
Every tool execution is monitored and validated. You receive detailed feedback about:
- Success/failure status with specific error messages
- Execution time and performance metrics
- Element validation and page state verification
- Suggested improvements and alternative approaches
- Screenshot evidence of before/after states

When a user gives you a task, analyze it and respond with tool calls in this JSON format:

{{"reasoning": "Brief explanation considering feedback", "tool_calls": [{{"tool": "tool_name", "arguments": {{"arg1": "value1"}}}}]}}

IMPORTANT RULES:
1. Always respond with valid JSON in the format above
2. Include reasoning that addresses previous feedback
3. Learn from execution feedback - if a tool failed, try alternative approaches
4. Use double quotes for ALL strings in JSON (NO backticks)
5. For JavaScript in script fields, use \\n for line breaks

Example with feedback consideration:
{{"reasoning": "Previous click failed with 'element not found'. Will try alternative selector and add wait.", "tool_calls": [{{"tool": "playwright_navigate", "arguments": {{"url": "https://google.com"}}}}, {{"tool": "playwright_wait_for_element", "arguments": {{"selector": "input[name='btnK']", "state": "visible", "timeout": 5000}}}}, {{"tool": "playwright_click", "arguments": {{"selector": "input[name='btnK']"}}}}]}}{feedback_section}
"""
    
    async def process_prompt(self, user_prompt: str) -> str:
        """Process a user prompt and execute browser automation tasks"""
        logger.info(f"Processing: {user_prompt}")
        
        # Check and ensure browser is ready before processing
        await self._ensure_browser_ready()
        
        # Add user prompt to conversation history
        self.conversation_history.append({"role": "user", "content": user_prompt})
        
        # Create messages for LLM
        messages = [
            {"role": "system", "content": self.create_system_message()},
            *self.conversation_history[-3:]  # Keep last 3 exchanges
        ]
        
        try:
            # Get response from LLM
            ai_response = await self.llm_provider.generate_response(messages)
            logger.info(f"LLM Response received")
            
            # Add AI response to conversation history
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            
            # Parse and execute tool calls
            if self.real_time_mode:
                execution_results = await self.execute_with_realtime_feedback(ai_response)
            else:
                execution_results = await self.execute_tool_calls_from_json(ai_response)
            
            if execution_results:
                return f"🤖 Analysis: {ai_response}\\n\\n📋 Execution Results:\\n{execution_results}"
            else:
                return f"🤖 {ai_response}"
            
        except Exception as e:
            error_msg = f"Error processing prompt: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    async def _ensure_browser_ready(self):
        """Ensure browser is ready and reinitialize if needed"""
        if self.use_mcp:
            # In MCP mode, browser is managed by MCP server, no validation needed
            logger.info("MCP mode: Browser managed by MCP server")
            return
            
        try:
            # Check if browser tools are initialized
            if not self.browser_tools or not hasattr(self.browser_tools, 'browser_initialized'):
                logger.info("Browser tools not initialized, reinitializing...")
                await self.browser_tools.initialize()
                return
            
            # Check if browser is alive
            browser_alive = await self.browser_tools.is_browser_alive()
            
            if not browser_alive:
                logger.info("Browser is not responsive, reinitializing...")
                print(f"🔄 Browser has been closed or is not responsive. Reopening {self._get_browser_display_name()}...")
                
                # Clean up current browser state completely
                try:
                    await self.browser_tools.cleanup_all()
                except Exception as cleanup_error:
                    logger.warning(f"Cleanup error (expected if browser was closed): {cleanup_error}")
                
                # Reset browser state flags
                self.browser_tools.browser_initialized = False
                self.browser_tools.browser = None
                self.browser_tools.context = None
                self.browser_tools.pages = []
                
                # Reinitialize browser completely
                success = await self.browser_tools.initialize()
                if success:
                    print(f"✅ {self._get_browser_display_name()} browser reopened successfully!")
                    logger.info(f"Browser successfully reinitialized: {self.browser_type}")
                else:
                    print(f"❌ Failed to reopen {self._get_browser_display_name()} browser")
                    raise Exception(f"Failed to reinitialize {self.browser_type} browser")
            else:
                logger.info("Browser is responsive and ready")
                
        except Exception as e:
            logger.error(f"Error ensuring browser ready: {e}")
            # Try complete reinitialization as last resort
            try:
                print(f"🔧 Attempting complete browser reinitialization...")
                
                # Force cleanup
                try:
                    await self.browser_tools.cleanup_all()
                except:
                    pass
                
                # Reset all state
                self.browser_tools.browser_initialized = False
                self.browser_tools.browser = None
                self.browser_tools.context = None
                self.browser_tools.pages = []
                
                # Reinitialize
                await self.browser_tools.initialize()
                print(f"✅ Browser reinitialized successfully!")
                
            except Exception as init_error:
                logger.error(f"Failed to reinitialize browser: {init_error}")
                print(f"❌ Critical error: Could not reinitialize browser. Please restart the agent.")
                raise Exception(f"Browser initialization failed: {init_error}")
    
    def _get_browser_display_name(self) -> str:
        """Get user-friendly browser display name"""
        browser_names = {
            "chromium": "Chromium",
            "firefox": "Firefox", 
            "webkit": "WebKit (Safari)",
            "chrome": "Google Chrome",
            "msedge": "Microsoft Edge"
        }
        return browser_names.get(self.browser_type, self.browser_type.title())
    
    async def execute_with_realtime_feedback(self, ai_response: str) -> str:
        """Execute tools one by one with real-time LLM feedback after each execution"""
        try:
            # Debug: Log the actual response
            logger.info(f"LLM Response (first 200 chars): {ai_response[:200]}...")
            
            # Extract JSON from response
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                logger.warning(f"No JSON found in AI response. Full response: {ai_response}")
                return "❌ No valid tool calls found in AI response"
            
            json_str = ai_response[json_start:json_end]
            logger.info(f"Extracted JSON: {json_str}")
            response_data = json.loads(json_str)
            
            if "tool_calls" not in response_data:
                logger.warning("No tool_calls found in JSON response")
                return "❌ No tool_calls found in response"
            
            # Initialize execution tracking
            results = []
            reasoning = response_data.get("reasoning", "No reasoning provided")
            results.append(f"💭 Initial Reasoning: {reasoning}")
            
            tool_calls = response_data["tool_calls"]
            executed_tools = []
            current_context = await self._capture_context_safely()
            
            # Execute tools one by one with real-time feedback
            for i, tool_call in enumerate(tool_calls):
                tool_name = tool_call.get("tool")
                arguments = tool_call.get("arguments", {})
                
                if not tool_name:
                    results.append(f"❌ Tool call {i+1}: Missing tool name")
                    continue
                
                # Resolve and execute through MCP or local direct call
                if self.use_mcp and self.mcp_client:
                    execution_result = await self._execute_mcp_tool_with_validation(tool_name, arguments, i+1)
                else:
                    tool_method = None
                    for tool_info in self.browser_tools.available_methods:
                        if tool_info['name'] == tool_name:
                            tool_method = tool_info['method']
                            break
                    if not tool_method:
                        results.append(f"❌ Tool call {i+1}: Tool '{tool_name}' not found")
                        continue
                    execution_result = await self._execute_tool_with_validation(
                        tool_method, tool_name, arguments, i+1
                    )
                
                # Create feedback object
                tool_feedback = ToolExecutionFeedback(tool_result=execution_result)
                
                # Get remaining tools
                remaining_tools = tool_calls[i+1:] if i+1 < len(tool_calls) else []
                
                # Send result to LLM for feedback
                llm_feedback = await self.real_time_feedback_loop.send_tool_result_to_llm(
                    tool_feedback, remaining_tools, current_context
                )
                
                # Log execution result with LLM feedback
                status_icon = "✅" if execution_result.success else "❌"
                assertion_icon = self._get_assertion_icon(tool_feedback.assertion_status)
                
                result_text = f"{status_icon} Tool {i+1} ({tool_name}): {execution_result.result_data}"
                result_text += f" [{assertion_icon} {tool_feedback.assertion_status}]"
                
                if tool_feedback.llm_feedback:
                    result_text += f" - LLM: {tool_feedback.llm_feedback[:100]}..."
                
                results.append(result_text)
                executed_tools.append(tool_feedback)
                
                # Process LLM decision
                next_action = tool_feedback.next_action_suggestion
                
                if next_action == "STOP":
                    results.append(f"🛑 LLM Decision: STOP execution (Confidence: {tool_feedback.confidence_score:.2f})")
                    break
                
                elif next_action == "RETRY":
                    results.append(f"🔄 LLM Decision: RETRY tool with modifications")
                    # Apply modifications if any
                    if tool_feedback.modification_requests:
                        results.append(f"📝 Modifications: {', '.join(tool_feedback.modification_requests)}")
                    # Retry logic could be implemented here
                
                elif next_action == "MODIFY":
                    results.append(f"🔧 LLM Decision: MODIFY approach for remaining tools")
                    if tool_feedback.modification_requests:
                        results.append(f"📝 Modifications: {', '.join(tool_feedback.modification_requests)}")
                    # Tool modification logic could be implemented here
                
                elif next_action == "CONTINUE":
                    if remaining_tools:
                        results.append(f"➡️  LLM Decision: CONTINUE to next tool")
                    else:
                        results.append(f"✅ LLM Decision: All tools completed successfully")
                
                # Check if LLM wants to stop
                if not tool_feedback.should_continue:
                    results.append(f"⏹️  LLM requested to stop execution")
                    break
                
                # Update context for next iteration
                current_context = await self._capture_context_safely()
            
            # Generate final summary
            assertion_summary = self.real_time_feedback_loop.get_assertion_summary()
            results.append(f"\\n📊 ASSERTION SUMMARY:")
            results.append(f"   Total: {assertion_summary['total']}, Pass: {assertion_summary['pass']}, Fail: {assertion_summary['fail']}, Retry: {assertion_summary['retry']}")
            results.append(f"   Success Rate: {assertion_summary['success_rate']:.1%}, Avg Confidence: {assertion_summary['average_confidence']:.2f}")
            
            # Store execution results for future reference
            self.execution_results.extend([tf.tool_result for tf in executed_tools])
            self.execution_results = self.execution_results[-10:]  # Keep last 10
            
            return "\\n".join(results)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return f"❌ Failed to parse tool calls: {e}"
        except Exception as e:
            logger.error(f"Error in real-time execution: {e}")
            return f"❌ Error in real-time execution: {e}"
    
    def _get_assertion_icon(self, assertion_status: str) -> str:
        """Get icon for assertion status"""
        icons = {
            "PASS": "✅",
            "FAIL": "❌", 
            "RETRY": "🔄",
            "PENDING": "⏳"
        }
        return icons.get(assertion_status, "❓")
    
    async def execute_tool_calls_from_json(self, ai_response: str) -> str:
        """Parse JSON response and execute tool calls directly"""
        try:
            # Debug: Log the actual response
            logger.info(f"LLM Response (first 200 chars): {ai_response[:200]}...")
            
            # Extract JSON from response
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                logger.warning(f"No JSON found in AI response. Full response: {ai_response}")
                # Try to provide a helpful fallback
                if ai_response.strip():
                    return f"🤖 {ai_response.strip()}"
                else:
                    return "❌ The AI model returned an empty response. Please try again with a simpler request."
            
            json_str = ai_response[json_start:json_end]
            logger.info(f"Extracted JSON: {json_str}")
            response_data = json.loads(json_str)
            
            if "tool_calls" not in response_data:
                logger.warning("No tool_calls found in JSON response")
                return ""
            
            results = []
            reasoning = response_data.get("reasoning", "No reasoning provided")
            results.append(f"💭 Reasoning: {reasoning}")
            
            # Store current execution results for feedback
            current_execution_results = []
            
            for i, tool_call in enumerate(response_data["tool_calls"], 1):
                tool_name = tool_call.get("tool")
                arguments = tool_call.get("arguments", {})
                
                if not tool_name:
                    results.append(f"❌ Tool call {i}: Missing tool name")
                    continue
                
                # Execute via MCP or locally
                if self.use_mcp and self.mcp_client:
                    execution_result = await self._execute_mcp_tool_with_validation(tool_name, arguments, i)
                else:
                    tool_method = None
                    for tool_info in self.browser_tools.available_methods:
                        if tool_info['name'] == tool_name:
                            tool_method = tool_info['method']
                            break
                    if not tool_method:
                        results.append(f"❌ Tool call {i}: Tool '{tool_name}' not found")
                        continue
                    execution_result = await self._execute_tool_with_validation(
                        tool_method, tool_name, arguments, i
                    )
                
                current_execution_results.append(execution_result)
                
                # Add result to display
                if execution_result.success:
                    result_text = f"✅ Tool {i} ({tool_name}): {execution_result.result_data}"
                    if execution_result.validation_results:
                        # Show key validation successes
                        validations = [k for k, v in execution_result.validation_results.items() if v is True]
                        if validations:
                            result_text += f" [Validated: {', '.join(validations[:2])}]"
                    results.append(result_text)
                else:
                    error_text = f"❌ Tool {i} ({tool_name}): {execution_result.error_message}"
                    if execution_result.suggestions:
                        error_text += f" [Suggestions: {', '.join(execution_result.suggestions[:2])}]"
                    results.append(error_text)
            
            # Generate feedback for next interaction
            if current_execution_results:
                self.execution_results.extend(current_execution_results)
                # Keep only last 10 results to avoid memory buildup
                self.execution_results = self.execution_results[-10:]
                
                # Generate feedback for LLM
                self.last_feedback = self.feedback_generator.generate_llm_feedback(current_execution_results)
            
            return "\\n".join(results)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return f"❌ Failed to parse tool calls: {e}"
        except Exception as e:
            logger.error(f"Error executing tool calls: {e}")
            return f"❌ Error executing tool calls: {e}"
    
    async def _execute_tool_with_validation(self, tool_method, tool_name: str, arguments: dict, tool_index: int) -> ToolExecutionResult:
        """Execute a tool with comprehensive validation and feedback"""
        result = ToolExecutionResult(tool_name=tool_name, success=False)
        start_time = time.time()
        
        try:
            # Capture context before execution
            result.context_before = await self._capture_context_safely()
            
            # Take screenshot before if it's a critical operation
            if tool_name in ['playwright_click', 'playwright_fill', 'playwright_navigate']:
                try:
                    screenshot_result = await self.browser_tools.playwright_screenshot()
                    if isinstance(screenshot_result, str) and 'screenshot' in screenshot_result:
                        result.screenshot_before = f"{tool_name}_before_{tool_index}.png"
                except:
                    pass  # Screenshots are optional
            
            # Check browser state before tool execution
            await self._ensure_browser_ready()
            
            # Execute the tool method
            if asyncio.iscoroutinefunction(tool_method):
                result.result_data = await tool_method(**arguments)
            else:
                result.result_data = tool_method(**arguments)
            
            result.execution_time = time.time() - start_time
            result.success = True
            
            # Capture context after execution
            result.context_after = await self._capture_context_safely()
            
            # Take screenshot after for critical operations
            if tool_name in ['playwright_click', 'playwright_fill', 'playwright_navigate']:
                try:
                    screenshot_result = await self.browser_tools.playwright_screenshot()
                    if isinstance(screenshot_result, str) and 'screenshot' in screenshot_result:
                        result.screenshot_after = f"{tool_name}_after_{tool_index}.png"
                except:
                    pass
            
            # Validate results based on tool type
            await self._validate_tool_result(result, arguments)
            
        except Exception as e:
            result.execution_time = time.time() - start_time
            result.error_message = str(e)
            result.success = False
            
            # Generate suggestions based on error
            result.suggestions = self._generate_error_suggestions(tool_name, str(e))
            
            # Handle browser state errors with retry
            if await self._is_browser_error(str(e)):
                retry_result = await self._retry_with_browser_recovery(tool_method, tool_name, arguments, tool_index)
                if retry_result.success:
                    retry_result.retry_count = 1
                    return retry_result
                else:
                    result.retry_count = 1
        
        return result
    
    async def _capture_context_safely(self) -> Dict[str, Any]:
        """Safely capture browser context without failing"""
        context = {}
        try:
            # Get basic page info
            page_info = await self.browser_tools.playwright_get_page_info()
            if isinstance(page_info, dict):
                context.update(page_info)
        except:
            pass
        return context
    
    async def _validate_tool_result(self, result: ToolExecutionResult, arguments: dict):
        """Validate tool execution results based on tool type"""
        if not self.result_validator:
            return
        
        try:
            if result.tool_name == "playwright_navigate":
                url = arguments.get("url", "")
                result.validation_results = await self.result_validator.validate_navigation(result, url)
            
            elif result.tool_name in ["playwright_click", "playwright_fill", "playwright_select"]:
                selector = arguments.get("selector", "")
                result.validation_results = await self.result_validator.validate_element_interaction(result, selector)
            
            elif result.tool_name in ["playwright_get_visible_text", "playwright_extract_content"]:
                selector = arguments.get("selector", "")
                result.validation_results = await self.result_validator.validate_content_extraction(result, selector)
                
        except Exception as e:
            result.validation_results["validation_error"] = str(e)
    
    def _generate_error_suggestions(self, tool_name: str, error_message: str) -> List[str]:
        """Generate helpful suggestions based on error patterns"""
        suggestions = []
        error_lower = error_message.lower()
        
        if "timeout" in error_lower:
            suggestions.append("Increase timeout value or add explicit wait")
            suggestions.append("Check if page is still loading")
        
        if "element" in error_lower or "selector" in error_lower:
            suggestions.append("Try alternative CSS selector")
            suggestions.append("Wait for element to be visible first")
            suggestions.append("Use playwright_find_element to locate element")
        
        if "navigation" in error_lower or "navigate" in error_lower:
            suggestions.append("Verify URL is accessible")
            suggestions.append("Check network connectivity")
        
        if tool_name == "playwright_click":
            suggestions.append("Ensure element is clickable and not covered")
            suggestions.append("Try using element coordinates instead")
        
        if tool_name == "playwright_fill":
            suggestions.append("Clear field before filling")
            suggestions.append("Check if element accepts text input")
        
        return suggestions[:3]  # Return top 3 suggestions
    
    async def _is_browser_error(self, error_message: str) -> bool:
        """Check if error is related to browser state"""
        browser_error_keywords = [
            "target page, context or browser has been closed",
            "browser has been closed",
            "context has been closed",
            "page has been closed",
            "browser connection lost",
            "browser disconnected"
        ]
        error_lower = error_message.lower()
        return any(keyword in error_lower for keyword in browser_error_keywords)
    
    async def _retry_with_browser_recovery(self, tool_method, tool_name: str, arguments: dict, tool_index: int) -> ToolExecutionResult:
        """Retry tool execution after browser recovery"""
        logger.warning(f"Browser error detected, attempting recovery for {tool_name}")
        result = ToolExecutionResult(tool_name=tool_name, success=False)
        
        try:
            # Reset browser state completely
            self.browser_tools.browser = None
            self.browser_tools.context = None
            self.browser_tools.pages = []
            self.browser_tools.browser_initialized = False
            
            # Reinitialize browser
            await self.browser_tools._ensure_browser_initialized()
            logger.info(f"Browser reinitialized successfully, retrying {tool_name}")
            
            # Retry the tool method
            start_time = time.time()
            if asyncio.iscoroutinefunction(tool_method):
                result.result_data = await tool_method(**arguments)
            else:
                result.result_data = tool_method(**arguments)
            
            result.execution_time = time.time() - start_time
            result.success = True
            result.result_data = f"[Recovered] {result.result_data}"
            
        except Exception as retry_e:
            result.error_message = f"Failed after browser recovery: {str(retry_e)}"
            result.success = False
        
        return result
    
    async def run_interactive(self):
        """Run the agent in interactive mode"""
        print(f"\\n🤖 AI Browser Automation Agent")
        print("=" * 70)
        print(f"🧠 LLM Provider: {self.llm_provider.provider_name.upper()}")
        print(f"🌐 Browser:      {self._get_browser_display_name()}")
        print(f"⚡ Mode:         {'🔄 Real-Time Feedback' if self.real_time_mode else '🚀 Batch Execution'}")
        tool_count = "49" if self.use_mcp else len(self.browser_tools.available_methods)
        print(f"🛠️  Tools:        {tool_count} available")
        print("=" * 70)
        print("Available commands:")
        print("  - Type your browser automation task")
        print("  - 'switch <provider>' or 'switch to <provider>' (openai/anthropic/gemini)")
        print("  - 'browser <type>' or 'browser to <type>' (chromium/firefox/webkit/chrome/msedge)")
        print("  - 'quit' to exit\\n")
        
        while True:
            try:
                user_input = input("👤 Your task: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye!")
                    break
                
                if user_input.lower().startswith('switch '):
                    # Handle both "switch gemini" and "switch to gemini" formats
                    switch_part = user_input[7:].strip().lower()
                    if switch_part.startswith('to '):
                        new_provider = switch_part[3:].strip()
                    else:
                        new_provider = switch_part
                    
                    # Validate provider name
                    valid_providers = ['openai', 'anthropic', 'gemini']
                    if new_provider not in valid_providers:
                        print(f"❌ Unknown provider '{new_provider}'. Valid options: {', '.join(valid_providers)}")
                        continue
                    
                    try:
                        self.llm_provider = self._initialize_llm_provider(new_provider)
                        print(f"✅ Switched to {self.llm_provider.provider_name.upper()}")
                        continue
                    except Exception as e:
                        print(f"❌ Failed to switch to {new_provider}: {e}")
                        continue
                
                if user_input.lower().startswith('browser '):
                    # Handle both "browser chromium" and "browser to chromium" formats
                    browser_part = user_input[8:].strip().lower()
                    if browser_part.startswith('to '):
                        new_browser = browser_part[3:].strip()
                    else:
                        new_browser = browser_part
                    
                    # Normalize browser type
                    new_browser = self.browser_tools._normalize_browser_type(new_browser)
                    valid_browsers = ['chromium', 'firefox', 'webkit', 'chrome', 'msedge']
                    
                    if new_browser in valid_browsers:
                        try:
                            # Cleanup current browser
                            await self.browser_tools.cleanup_all()
                            
                            # Initialize new browser tools
                            self.browser_type = new_browser
                            self.browser_tools = DirectBrowserTools(new_browser)
                            await self.browser_tools.initialize()
                            
                            print(f"✅ Switched to {new_browser.title()} browser")
                            continue
                        except Exception as e:
                            print(f"❌ Failed to switch to {new_browser}: {e}")
                            continue
                    else:
                        print(f"❌ Invalid browser. Choose from: {', '.join(valid_browsers)}")
                        continue
                
                if not user_input:
                    continue
                
                print("\\n🤖 Processing your request...\\n")
                response = await self.process_prompt(user_input)
                print(f"{response}\\n")
                print("-" * 60)
                
            except KeyboardInterrupt:
                print("\\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
    
    async def cleanup(self):
        """Clean up resources"""
        if self.initialized:
            if self.use_mcp:
                # In MCP mode, cleanup is handled by MCP server
                if self.mcp_client:
                    await self.mcp_client.stop_server()
            else:
                # In local mode, cleanup browser tools
                if self.browser_tools:
                    await self.browser_tools.cleanup_all()

    async def _execute_mcp_tool_with_validation(self, tool_name: str, arguments: dict, tool_index: int) -> ToolExecutionResult:
        """Execute a tool via MCP server with validation wrapper."""
        result = ToolExecutionResult(tool_name=tool_name, success=False)
        start_time = time.time()
        try:
            # Capture context before
            result.context_before = await self._capture_context_safely()
            await self._ensure_browser_ready()
            if not self.mcp_client:
                raise RuntimeError("MCP client not initialized")
            # Call tool via MCP (to be implemented in client)
            mcp_response = await self.mcp_client.call_tool(tool_name, arguments)
            result.result_data = mcp_response
            result.execution_time = time.time() - start_time
            result.success = True
            result.context_after = await self._capture_context_safely()
            await self._validate_tool_result(result, arguments)
        except Exception as e:
            result.execution_time = time.time() - start_time
            result.error_message = str(e)
            result.success = False
            result.suggestions = self._generate_error_suggestions(tool_name, str(e))
        return result

def show_welcome():
    """Display welcome screen"""
    print("\n" + "="*80)
    print("🤖 AI BROWSER AUTOMATION AGENT - ENHANCED")
    print("="*80)
    print("An intelligent agent that can automate browser tasks using natural language")
    print("Powered by multiple LLM providers and Playwright browser automation")
    print("="*80)

def select_llm_provider():
    """Interactive LLM provider selection"""
    print("\n🧠 SELECT LLM PROVIDER:")
    print("-" * 40)
    
    providers = [
        ("OpenAI GPT-4", "openai", "OPENAI_API_KEY"),
        ("Anthropic Claude", "anthropic", "ANTHROPIC_API_KEY"), 
        ("Google Gemini", "gemini", "GEMINI_API_KEY")
    ]
    
    # Show available providers with status
    for i, (name, key, env_key) in enumerate(providers, 1):
        status = "✅ Ready" if os.getenv(env_key) else "❌ No API key"
        print(f"{i}. {name.ljust(20)} - {status}")
    
    while True:
        try:
            choice = input(f"\nSelect LLM provider (1-{len(providers)}): ").strip()
            choice_num = int(choice)
            
            if 1 <= choice_num <= len(providers):
                selected = providers[choice_num - 1]
                api_key = os.getenv(selected[2])
                
                if not api_key:
                    print(f"❌ Warning: {selected[2]} not found in environment variables")
                    confirm = input("Continue anyway? (y/N): ").strip().lower()
                    if confirm != 'y':
                        continue
                
                print(f"✅ Selected: {selected[0]}")
                return selected[1]
            else:
                print(f"❌ Please enter a number between 1 and {len(providers)}")
                
        except ValueError:
            print("❌ Please enter a valid number")
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)

def select_browser():
    """Interactive browser selection"""
    print("\n🌐 SELECT BROWSER ENGINE:")
    print("-" * 40)
    
    browsers = [
        ("Chromium", "chromium", "Default Playwright Chromium - Fast and reliable"),
        ("Firefox", "firefox", "Mozilla Firefox - Good for cross-browser testing"),
        ("WebKit", "webkit", "Safari engine - Best for Safari compatibility"),
        ("Chrome", "chrome", "Google Chrome - If installed locally"),
        ("Microsoft Edge", "msedge", "Edge browser - If installed locally")
    ]
    
    # Show available browsers
    for i, (name, key, description) in enumerate(browsers, 1):
        print(f"{i}. {name.ljust(15)} - {description}")
    
    while True:
        try:
            choice = input(f"\nSelect browser (1-{len(browsers)}) [1]: ").strip()
            
            # Default to Chromium if empty
            if not choice:
                choice = "1"
                
            choice_num = int(choice)
            
            if 1 <= choice_num <= len(browsers):
                selected = browsers[choice_num - 1]
                print(f"✅ Selected: {selected[0]} ({selected[1]})")
                return selected[1]
            else:
                print(f"❌ Please enter a number between 1 and {len(browsers)}")
                
        except ValueError:
            print("❌ Please enter a valid number")
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)

def show_configuration(llm_provider, browser_type):
    """Display selected configuration"""
    print("\n📋 CONFIGURATION SUMMARY:")
    print("-" * 40)
    print(f"LLM Provider: {llm_provider.upper()}")
    print(f"Browser:      {browser_type.title()}")
    print("-" * 40)
    
    confirm = input("Proceed with this configuration? (Y/n): ").strip().lower()
    return confirm in ['', 'y', 'yes']

def select_execution_mode():
    """Select execution mode: batch or real-time feedback"""
    print("\\n" + "="*50)
    print("⚡ EXECUTION MODE SELECTION")
    print("="*50)
    print("1. 🚀 Batch Mode (Traditional - Execute all tools at once)")
    print("2. 🔄 Real-Time Feedback Mode (LLM feedback after each tool)")
    print("="*50)
    
    while True:
        try:
            choice = input("\\n👉 Enter your choice (1-2): ").strip()
            if choice == "1":
                return False  # Batch mode
            elif choice == "2":
                return True   # Real-time mode
            else:
                print("❌ Invalid choice. Please enter 1 or 2.")
        except (ValueError, KeyboardInterrupt):
            print("\\n❌ Invalid input. Please try again.")

def select_transport_mode():
    """Select transport mode: local or MCP"""
    print("\\n" + "="*50)
    print("🔌 TRANSPORT MODE SELECTION")
    print("="*50)
    print("1. 🏠 Local Mode (Direct tool calls - faster)")
    print("2. 📡 MCP Mode (JSON-RPC over stdio - protocol compliant)")
    print("="*50)
    
    while True:
        try:
            choice = input("\\n👉 Enter your choice (1-2) [1]: ").strip()
            if choice == "" or choice == "1":
                return False  # Local mode
            elif choice == "2":
                return True   # MCP mode
            else:
                print("❌ Invalid choice. Please enter 1 or 2.")
        except (ValueError, KeyboardInterrupt):
            print("\\n❌ Invalid input. Please try again.")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="AI Browser Automation Agent (Enhanced)")
    parser.add_argument('--llm', choices=['openai', 'anthropic', 'gemini'], 
                       help='LLM provider to use (skips interactive selection)')
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit', 'chrome', 'msedge'],
                       help='Browser type to use (skips interactive selection)')
    parser.add_argument('--mode', choices=['batch', 'realtime'],
                       help='Execution mode to use (skips interactive selection)')
    parser.add_argument('--transport', choices=['local', 'mcp'], default='local',
                       help='Tool transport: local (in-process) or mcp (JSON-RPC via MCP server)')
    parser.add_argument('--list-providers', action='store_true', 
                       help='List available providers and exit')
    parser.add_argument('--quick', action='store_true',
                       help='Quick start with default settings (OpenAI + Chromium)')
    return parser.parse_args()

async def main():
    """Main function with enhanced CLI"""
    args = parse_arguments()
    
    # Handle list providers option
    if args.list_providers:
        print("\\n🔍 Available LLM Providers:")
        print("=" * 40)
        providers = [
            ("OpenAI", "OPENAI_API_KEY"),
            ("Anthropic", "ANTHROPIC_API_KEY"), 
            ("Gemini", "GEMINI_API_KEY")
        ]
        for provider, env_key in providers:
            status = "✅ Ready" if os.getenv(env_key) else "❌ No API key"
            print(f"{provider.ljust(12)}: {status}")
        
        print("\\n🌐 Available Browser Engines:")
        print("=" * 40)
        browsers = ["Chromium", "Firefox", "WebKit", "Chrome", "Microsoft Edge"]
        for browser in browsers:
            print(f"{browser.ljust(15)}: ✅ Available")
        return
    
    # Show welcome screen
    show_welcome()
    
    # Determine LLM provider
    if args.quick:
        llm_provider = "openai"
        browser_type = "chromium"
        real_time_mode = False
        print("\\n🚀 Quick start mode: OpenAI + Chromium + Batch Mode")
    elif args.llm:
        llm_provider = args.llm
    else:
        llm_provider = select_llm_provider()
    
    # Determine browser type
    if not args.quick:
        if args.browser:
            browser_type = args.browser
        else:
            browser_type = select_browser()
        
        # Select execution mode (use flag if provided)
        if args.mode:
            real_time_mode = (args.mode == 'realtime')
        else:
            real_time_mode = select_execution_mode()
        
        # Select transport mode (use flag if provided)
        if args.transport != 'local':  # Only use flag if explicitly set to non-default
            use_mcp = (args.transport == 'mcp')
        else:
            use_mcp = select_transport_mode()
    else:
        # Quick mode defaults
        use_mcp = (args.transport == 'mcp')
    
    # Show configuration and confirm
    if not args.quick and not show_configuration(llm_provider, browser_type):
        print("❌ Configuration cancelled")
        return
    
    # Initialize and run agent
    print(f"\n🚀 Starting AI Browser Agent...")
    print(f"   Mode: {'🔄 Real-Time Feedback' if real_time_mode else '🚀 Batch Execution'}")
    print(f"   Transport: {'📡 MCP (JSON-RPC)' if use_mcp else '🏠 Local (Direct)'}")
    agent = AIBrowserAgent(llm_provider, browser_type, use_mcp=use_mcp)
    agent.real_time_mode = real_time_mode  # Set the execution mode
    
    try:
        success = await agent.initialize()
        if success:
            await agent.run_interactive()
        else:
            print("❌ Failed to initialize agent")
    except KeyboardInterrupt:
        print("\\nShutting down...")
    finally:
        await agent.cleanup()

if __name__ == "__main__":
    asyncio.run(main())

"""Main entry point for the AI Agent."""
import sys
from config import Config
from llm_integration import LLMIntegration
from action_executor import ActionExecutor
from ui import UserInterface
from logger import logger


class AIAgent:
    """Main AI Agent class that coordinates all components."""
    
    def __init__(self):
        """Initialize the AI Agent."""
        # Validate configuration
        is_valid, error_msg = Config.validate()
        if not is_valid:
            print(f"Configuration error: {error_msg}")
            print("Please check your .env file or environment variables.")
            sys.exit(1)
        
        # Initialize components
        try:
            self.llm = LLMIntegration()
            self.executor = ActionExecutor()
            self.ui = UserInterface()
            logger.log_action("agent_started", {"provider": Config.LLM_PROVIDER})
        except Exception as e:
            logger.log_error("Failed to initialize agent", e)
            print(f"Initialization error: {e}")
            sys.exit(1)
    
    def run(self):
        """Run the main agent loop."""
        try:
            while True:
                # Get user input
                user_input = self.ui.get_user_input()
                if user_input is None:
                    break
                
                if not user_input.strip():
                    continue
                
                # Show thinking indicator
                self.ui.show_llm_thinking()
                
                # Get LLM response
                try:
                    llm_response = self.llm.send_prompt(user_input)
                except Exception as e:
                    logger.log_error("LLM request failed", e)
                    self.ui.show_error(f"Failed to get LLM response: {e}")
                    continue
                
                # Parse LLM response
                action = self.executor.parse_llm_response(llm_response)
                if action is None:
                    self.ui.show_error("Failed to parse LLM response")
                    continue
                
                # Show action being taken
                action_type = action.get("action_type", "unknown")
                explanation = action.get("explanation", "")
                self.ui.show_action(action_type, explanation)
                
                # Execute action
                result = self.executor.execute_action(action, require_confirmation=True)
                
                # Handle confirmation requirement
                if result[0] is None and result[1] == "CONFIRMATION_REQUIRED":
                    action_details = action.get("action_details", {})
                    if self.ui.request_confirmation(action_type, action_details):
                        # Execute without confirmation requirement
                        result = self.executor.execute_action(action, require_confirmation=False)
                    else:
                        self.ui.show_result(False, "Action cancelled by user")
                        logger.log_action("action_cancelled", {"action_type": action_type})
                        continue
                
                # Display result
                success, message = result
                if action_type == "information":
                    self.ui.show_information(message)
                else:
                    self.ui.show_result(success, message)
                
        except KeyboardInterrupt:
            logger.log_action("agent_stopped", {"reason": "keyboard_interrupt"})
        except Exception as e:
            logger.log_error("Unexpected error in main loop", e)
            self.ui.show_error(f"Unexpected error: {e}")
        finally:
            self.ui.show_goodbye()


def main():
    """Main function."""
    agent = AIAgent()
    agent.run()


if __name__ == "__main__":
    main()


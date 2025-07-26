# Changelog

## [2.0.0] - 2024-12-19

### Added
- **Chat Context Support**: Bot now receives the last 50 messages from the chat as context
- **Mention-based Responses**: Bot only responds when mentioned with `@bot_name` or `@id{bot_id}`
- **Enhanced Context Processing**: New method `on_message_with_context()` in DialogueTracker
- **Chat History Retrieval**: Function `get_chat_history()` to fetch recent messages from VK API

### Changed
- Modified `handle_message()` to include chat context processing
- Updated message handling to check for bot mentions before processing
- Enhanced system prompts to include chat context information

### Technical Details
- Uses VK API `messages.getHistory` method to retrieve chat history
- Processes user information to display names in context
- Maintains backward compatibility with existing dialogue tracking
- Filters messages to only include user messages (excludes bot and group messages)

### Files Modified
- `vk_bot.py`: Added chat history retrieval and mention detection
- `dialogue_tracker.py`: Added context-aware message processing
- `README.md`: Updated documentation with new features 
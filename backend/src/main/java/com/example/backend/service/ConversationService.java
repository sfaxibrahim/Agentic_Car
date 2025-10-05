package com.example.backend.service;

import com.example.backend.model.*;
import com.example.backend.repository.ConversationRepository;
import com.example.backend.repository.MessageRepository;
import com.example.backend.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Arrays;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class ConversationService {

    private final ConversationRepository conversationRepository;
    private final MessageRepository messageRepository;
    private final UserRepository userRepository;

    public Conversation createConversation(UUID userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("User not found by ID " + userId));

        Conversation conv = new Conversation();
        conv.setUser(user);
        conv.setTitle("New conversation");
        return conversationRepository.save(conv);
    }



    public List<Conversation> listUserConversations(UUID userId) {
        User user = userRepository.findById(userId).orElseThrow();
        return conversationRepository.findByUserOrderByUpdatedAtDesc(user);
    }

    @Transactional
    public void deleteConversation(UUID conversationId){
        Conversation conv = conversationRepository.findById(conversationId)
                .orElseThrow(() -> new RuntimeException("Conversation Not Found"));

        messageRepository.deleteByConversation(conv);
        conversationRepository.delete(conv);
    }

    @Transactional
    public Message addMessage(UUID conversationId, MessageRole role, String content) {
        Conversation conv = conversationRepository.findById(conversationId).orElseThrow();
        Message message = new Message();
        message.setConversation(conv);
        message.setRole(role);
        message.setContent(content);
        Message saved = messageRepository.save(message);

        // Auto-generate title from first user message
        if ((conv.getTitle() == null || conv.getTitle().isBlank() || conv.getTitle().equals("New conversation"))
                && role == MessageRole.USER) {
            String generatedTitle = generateTitleFromContent(content);
            conv.setTitle(generatedTitle);
            conversationRepository.save(conv);
        }

        // Update conversation timestamp
        conversationRepository.save(conv);

        return saved;
    }

    // Helper method to generate title from content
    private String generateTitleFromContent(String content) {
        if (content == null || content.isBlank()) {
            return "New conversation";
        }

        // Clean the content
        String cleaned = content.trim();

        // Remove common file attachments notation
        cleaned = cleaned.replaceAll("\\[File:.*?\\]", "").trim();

        if (cleaned.isBlank()) {
            return "New conversation";
        }

        // Take first 5 words
        String[] words = cleaned.split("\\s+");
        String title = String.join(" ", Arrays.copyOfRange(words, 0, Math.min(5, words.length)));

        // Limit title length to 50 characters
        if (title.length() > 50) {
            title = title.substring(0, 47) + "...";
        }

        return title;
    }

    @Transactional
    public Conversation updateConversationTitle(UUID conversationId, String newTitle) {
        Conversation conv = conversationRepository.findById(conversationId).orElseThrow();
        conv.setTitle(newTitle);
        return conversationRepository.save(conv);
    }

    public Conversation getConversationById(UUID id) {
        return conversationRepository.findById(id).orElseThrow();
    }

    public List<Message> getMessages(UUID conversationId) {
        Conversation conv = conversationRepository.findById(conversationId).orElseThrow();
        return messageRepository.findByConversationOrderByCreatedAtAsc(conv);
    }

    // Get last N messages (used to load context)
    public List<Message> getLastNMessages(UUID conversationId, int n) {
        Conversation conv = conversationRepository.findById(conversationId).orElseThrow();
        return messageRepository.findByConversationOrderByCreatedAtDesc(conv, PageRequest.of(0, n));
    }
}
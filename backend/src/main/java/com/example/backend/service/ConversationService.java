package com.example.backend.service;

import com.example.backend.model.*;
import com.example.backend.repository.ConversationRepository;
import com.example.backend.repository.MessageRepository;
import com.example.backend.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class ConversationService {

    private final ConversationRepository conversationRepository;
    private final MessageRepository messageRepository;
    private final UserRepository userRepository;

    public Conversation createConversation(UUID userId, String title) {
        User user = userRepository.findById(userId).orElseThrow();
        Conversation conv = new Conversation();
        conv.setUser(user);
        conv.setTitle(title == null || title.isBlank() ? "New conversation" : title);
        conv = conversationRepository.save(conv);
        return conv;
    }

    public List<Conversation> listUserConversations(UUID userId) {
        User user = userRepository.findById(userId).orElseThrow();
        return conversationRepository.findByUserOrderByUpdatedAtDesc(user);
    }

    @Transactional
    public Message addMessage(UUID conversationId, MessageRole role, String content) {
        Conversation conv = conversationRepository.findById(conversationId).orElseThrow();
        Message message = new Message();
        message.setConversation(conv);
        message.setRole(role);
        message.setContent(content);
        Message saved = messageRepository.save(message);

        // update conversation timestamp (UpdateTimestamp handles updatedAt, but explicitly save to be safe)
        conversationRepository.save(conv);
        return saved;
    }

    public Conversation getConversationById(UUID id) {
        return conversationRepository.findById(id).orElseThrow();
    }
    public List<Message> getMessages(UUID conversationId) {
        Conversation conv = conversationRepository.findById(conversationId).orElseThrow();
        return messageRepository.findByConversationOrderByCreatedAtAsc(conv);
    }

    // get last N messages (used to load context)
    public List<Message> getLastNMessages(UUID conversationId, int n) {
        Conversation conv = conversationRepository.findById(conversationId).orElseThrow();
        return messageRepository.findByConversationOrderByCreatedAtDesc(conv, PageRequest.of(0, n));
    }
}

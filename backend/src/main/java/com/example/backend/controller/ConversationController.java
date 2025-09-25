package com.example.backend.controller;

import com.example.backend.model.*;
import com.example.backend.repository.ConversationRepository;
import com.example.backend.service.ConversationService;
import com.example.backend.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.*;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/conversations")
@RequiredArgsConstructor
public class ConversationController {

    private final ConversationService conversationService;
    private final UserRepository userRepository;
    private final ConversationRepository conversationRepository;

    // create new conversation
    @PostMapping
    public ResponseEntity<?> createConversation(@RequestBody Map<String, String> body, Authentication auth) {
        String title = body.get("title");
        String username = auth.getName(); // from SecurityContext
        var user = userRepository.findByUsername(username).orElseThrow();
        Conversation conv = conversationService.createConversation(user.getId(), title);
        return ResponseEntity.ok(Map.of("id", conv.getId(), "title", conv.getTitle()));
    }

    // list user's conversations
    @GetMapping
    public ResponseEntity<?> listConversations(Authentication auth) {
        String username = auth.getName();
        var user = userRepository.findByUsername(username).orElseThrow();
        var convs = conversationService.listUserConversations(user.getId());
        var dto = convs.stream().map(c -> Map.of(
                "id", c.getId(),
                "title", c.getTitle(),
                "createdAt", c.getCreatedAt(),
                "updatedAt", c.getUpdatedAt()
        )).collect(Collectors.toList());
        return ResponseEntity.ok(dto);
    }

    // FIXED: Change from GET to PATCH for updating conversation
    @PatchMapping("/{id}")
    public ResponseEntity<?> patchConversation(@PathVariable UUID id, @RequestBody Map<String, String> body, Authentication auth) {
        String username = auth.getName();
        var user = userRepository.findByUsername(username).orElseThrow();
        Conversation conv = conversationService.getConversationById(id);
        if (!conv.getUser().getId().equals(user.getId())) {
            return ResponseEntity.status(403).body(Map.of("error", "Forbidden"));
        }
        String newTitle = body.get("title");
        if (newTitle != null) {
            conv.setTitle(newTitle);
            conversationRepository.save(conv); // inject repo or call service method
        }
        return ResponseEntity.ok(Map.of("id", conv.getId(), "title", conv.getTitle()));
    }

    // ADD: Delete conversation endpoint (referenced in frontend)
    @DeleteMapping("/{id}")
    public ResponseEntity<?> deleteConversation(@PathVariable UUID id, Authentication auth) {
        String username = auth.getName();
        var user = userRepository.findByUsername(username).orElseThrow();
        Conversation conv = conversationService.getConversationById(id);
        if (!conv.getUser().getId().equals(user.getId())) {
            return ResponseEntity.status(403).body(Map.of("error", "Forbidden"));
        }
        conversationRepository.delete(conv);
        return ResponseEntity.ok(Map.of("message", "Conversation deleted successfully"));
    }

    // list messages in conversation
    @GetMapping("/{id}/messages")
    public ResponseEntity<?> getMessages(@PathVariable UUID id, Authentication auth) {
        // optional: check conversation belongs to user
        var messages = conversationService.getMessages(id);
        var dto = messages.stream().map(m -> Map.of(
                "id", m.getId(),
                "role", m.getRole(),
                "content", m.getContent(),
                "createdAt", m.getCreatedAt()
        )).collect(Collectors.toList());
        return ResponseEntity.ok(dto);
    }

    // add a message (user or assistant) to conversation
    @PostMapping("/{id}/messages")
    public ResponseEntity<?> addMessage(@PathVariable UUID id, @RequestBody Map<String, String> body, Authentication auth) {
        String roleStr = body.get("role");
        String content = body.get("content");
        MessageRole role = MessageRole.valueOf(roleStr.toUpperCase());
        Message msg = conversationService.addMessage(id, role, content);
        return ResponseEntity.ok(Map.of("id", msg.getId(), "createdAt", msg.getCreatedAt()));
    }
}
package com.example.backend.controller;

import java.util.Map;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.example.backend.service.ChatService;

@CrossOrigin(origins = "http://localhost:3000")
@RestController
@RequestMapping("/api/chat")
public class ChatRestController {

    @Autowired
    private ChatService chatService;

    @PostMapping
    public String askQuestion(@RequestBody  Map<String, String> request) {
        return chatService.askAI(request.get("question"));
    }
}

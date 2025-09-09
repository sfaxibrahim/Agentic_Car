package com.example.backend.service;

import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

@Service
public class ChatService {
    private final RestTemplate restTemplate = new RestTemplate();
    private final String AI_API_URL = "http://localhost:8000/chat";

    public String askAI(String question) {
        Map<String, String> request = Map.of("question", question);
        Map<String, String> response = restTemplate.postForObject(AI_API_URL, request, Map.class);
        return response != null ? response.get("answer") : "AI service unavailable";
    }
}
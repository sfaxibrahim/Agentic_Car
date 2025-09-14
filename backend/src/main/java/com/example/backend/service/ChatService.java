package com.example.backend.service;

import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.core.io.buffer.DataBufferUtils;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
// import org.springframework.web.client.RestTemplate;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;

import java.nio.charset.StandardCharsets;
import java.util.Map;
@Service
public class ChatService {

    private final WebClient webClient;

    public ChatService() {
        this.webClient = WebClient.builder()
                .baseUrl("http://localhost:8000")
                .codecs(configurer -> {
                    configurer.defaultCodecs().maxInMemorySize(1024 * 1024); // 1MB
                    configurer.defaultCodecs().enableLoggingRequestDetails(true);
                })
                .build();
    }

    public Flux<String> streamChatResponse(String question) {
        return webClient
                .post()
                .uri("/chat/stream")
                .bodyValue(Map.of("question", question))
                .accept(MediaType.TEXT_PLAIN)
                .retrieve()
                .bodyToFlux(String.class)  // This is the key - let Spring handle it naturally
                .onErrorResume(error -> {
                    System.err.println("Error in stream: " + error.getMessage());
                    return Flux.just("Error: " + error.getMessage());
                });
    }
}

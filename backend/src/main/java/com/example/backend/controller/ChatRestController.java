package com.example.backend.controller;

import java.util.Map;

import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Flux;




import com.example.backend.service.ChatService;

@CrossOrigin(origins = "http://localhost:3000")
@RestController
@RequestMapping("/api/chat")
public class ChatRestController {

    private final ChatService chatService;

    public ChatRestController(ChatService chatService){
        this.chatService=chatService;
    }


    //@PostMapping
    //public String askQuestion(@RequestBody  Map<String, String> request) {
      //  return chatService.askAI(request.get("question"));
    //}
    @PostMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<String>> streamChat(@RequestBody Map<String, String> request) {

        return chatService.streamChatResponse(request.get("question"))
                .map(chunk -> ServerSentEvent.<String>builder()
                        .data(chunk)
                        .build())
                .doOnError(error -> System.err.println("Stream error: " + error.getMessage()))
                .onErrorResume(error ->
                        Flux.just(ServerSentEvent.<String>builder()
                                .data("Error occurred: " + error.getMessage())
                                .build())
                );
    }

    // Alternative endpoint - plain text streaming (like OpenAI API)
    @PostMapping(value = "/stream-plain", produces = MediaType.TEXT_PLAIN_VALUE)
    public Flux<String> streamChatPlain(@RequestBody Map<String, String> request) {
        return chatService.streamChatResponse(request.get("question"));
    }

}

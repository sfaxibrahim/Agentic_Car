package com.example.backend.repository;

import com.example.backend.model.Conversation;
import com.example.backend.model.Message;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;
@Repository
public interface MessageRepository extends JpaRepository<Message, UUID> {
    List<Message> findByConversationOrderByCreatedAtAsc(Conversation conversation);
    void deleteByConversation(Conversation conversation);

    List<Message> findByConversationOrderByCreatedAtDesc(Conversation conversation, Pageable pageable);

}


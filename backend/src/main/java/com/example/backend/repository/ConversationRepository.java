package com.example.backend.repository;

import com.example.backend.model.Conversation;
import com.example.backend.model.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
@Repository
public interface ConversationRepository  extends JpaRepository<Conversation, UUID> {
    List<Conversation> findByUserOrderByUpdatedAtDesc(User user);
}

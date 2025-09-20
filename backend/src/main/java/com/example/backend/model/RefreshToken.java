package com.example.backend.model;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.Instant;
import java.util.UUID;
@Getter
@Setter
@Entity
public class RefreshToken {
    @Id
    @GeneratedValue
    private UUID id;
    @Column(nullable=false, unique=true)
    private String token;
    @ManyToOne
    private User user;
    private Instant expiryDate;
    private boolean revoked=false;


}
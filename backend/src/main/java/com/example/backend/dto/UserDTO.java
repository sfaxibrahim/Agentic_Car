package com.example.backend.dto;

public class UserDTO {
    private String username;
    private String email;

    public UserDTO(String username, String email) {
        this.username = username;
        this.email = email;
    }

    // getters
    public String getUsername() { return username; }
    public String getEmail() { return email; }
}

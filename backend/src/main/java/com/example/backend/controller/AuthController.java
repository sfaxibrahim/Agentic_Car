package com.example.backend.controller;

import com.example.backend.config.GoogleVerifier;
import com.example.backend.config.JwtUtil;
import com.example.backend.dto.*;
import com.example.backend.model.RefreshToken;
import com.example.backend.model.User;
import com.example.backend.service.AuthService;
import com.example.backend.service.LoginService;
import com.example.backend.service.RefreshTokenService;
import com.google.api.client.googleapis.auth.oauth2.GoogleIdToken;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;
    private final LoginService loginService;
    private final RefreshTokenService refreshTokenService;
    private final AuthenticationManager authenticationManager;
    private final JwtUtil jwtUtil;
    private final GoogleVerifier googleVerifier; // <-- inject


    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody LoginRequest request){
        try {
            JwtResponse tokens = loginService.login(request.getUsername(), request.getPassword());
            return ResponseEntity.ok(tokens);
        } catch (Exception e){
            return ResponseEntity.status(401).body(e.getMessage());
        }
    }

    // FIXED: Refresh token endpoint
    @PostMapping("/refresh")
    public ResponseEntity<?> refreshToken(@RequestBody TokenRefreshRequest request){
        try {
            RefreshToken newToken = refreshTokenService.refreshToken(request.getRefreshToken());

            // Generate new access token
            String newAccessToken = jwtUtil.generateAccessToken(newToken.getUser().getUsername(), "USER");

            // Return new access token and refresh token
            return ResponseEntity.ok(new JwtResponse(newAccessToken, newToken.getToken()));
        } catch (Exception e){
            return ResponseEntity.status(401).body(e.getMessage());
        }
    }

    @PostMapping("/register")
    public ResponseEntity<?> register(@RequestBody RegisterRequest request){
        try {
            User user = authService.registerUser(request.getUsername(), request.getEmail(), request.getPassword());
            return ResponseEntity.ok("User registered successfully: " + user.getId());
        } catch (Exception e){
            return ResponseEntity.badRequest().body(e.getMessage());
        }
    }

    @PostMapping("/google")
    public ResponseEntity<?> googleLogin(@RequestBody GoogleTokenRequest request) {
        try {
            GoogleIdToken.Payload payload = googleVerifier.verify(request.getToken()); // <-- use bean

            if (payload == null) {
                return ResponseEntity.status(401).body("Invalid Google token");
            }

            String email = payload.getEmail();
            String name = (String) payload.get("name");

            User user = authService.findOrCreateGoogleUser(email, name);

            String accessToken = jwtUtil.generateAccessToken(user.getUsername(), "USER");
            RefreshToken refreshToken = refreshTokenService.createRefreshToken(user.getId());

            return ResponseEntity.ok(new JwtResponse(accessToken, refreshToken.getToken()));
        } catch (Exception e) {
            return ResponseEntity.status(401).body("Google login failed: " + e.getMessage());
        }
    }

}
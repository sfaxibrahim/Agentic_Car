package com.example.backend.service;

import com.example.backend.model.RefreshToken;
import com.example.backend.model.User;
import com.example.backend.repository.RefreshTokenRepository;
import com.example.backend.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class RefreshTokenService {
    private final RefreshTokenRepository refreshTokenRepository;
    private final UserRepository userRepository;
    private long refreshTokenDurationsMs=7*24*60*60*1000;//7day

    public RefreshToken createRefreshToken(UUID userId){
        User user=userRepository.findById(userId).orElseThrow();
        RefreshToken refreshToken=new RefreshToken();
        refreshToken.setUser(user);
        refreshToken.setToken(UUID.randomUUID().toString());
        refreshToken.setExpiryDate(Instant.now().plusMillis(refreshTokenDurationsMs));
        return  refreshTokenRepository.save(refreshToken);
    }
    // REFRESH TOKEN
    public RefreshToken refreshToken(String tokenString){
        RefreshToken token = refreshTokenRepository.findByToken(tokenString)
                .orElseThrow(() -> new RuntimeException("Refresh token not found"));

        if(token.getExpiryDate().isBefore(Instant.now()) || token.isRevoked()){
            throw new RuntimeException("Refresh token expired or revoked");
        }

        // optional: revoke old token and create new
        token.setRevoked(true);
        refreshTokenRepository.save(token);

        return createRefreshToken(token.getUser().getId());
    }


}

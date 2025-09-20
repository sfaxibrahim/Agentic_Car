package com.example.backend.service;

import com.example.backend.config.JwtUtil;
import com.example.backend.dto.JwtResponse;
import com.example.backend.model.RefreshToken;
import com.example.backend.model.User;
import com.example.backend.repository.UserRepository;
import lombok.AllArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

@Service
@AllArgsConstructor
public class LoginService {
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;
    private final RefreshTokenService refreshTokenService;

    public JwtResponse login(String username,String password)throws Exception{
        User user =userRepository.findByUsername(username).orElseThrow(()->new Exception("User not Found"));
        if (!passwordEncoder.matches(password,user.getPassword())){
            throw new Exception("Invalid credentials");
        }
        //Generate JWT acces Token
        String accessToken=jwtUtil.generateAccessToken(user.getUsername(),"User");

        //Generate refresh Token
        RefreshToken refreshToken= refreshTokenService.createRefreshToken(user.getId());
        return new JwtResponse(accessToken,refreshToken.getToken());
    }

}

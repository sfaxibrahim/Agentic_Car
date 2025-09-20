package com.example.backend.service;

import com.example.backend.dto.LoginRequest;
import com.example.backend.dto.LoginResponse;
import com.example.backend.model.User;
import com.example.backend.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

import java.util.Optional;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepository;
    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    public LoginResponse login(LoginRequest request) {
        Optional<User> userOpt = userRepository.findByUsername(request.getUsername());
        if (userOpt.isPresent()) {
            User user = userOpt.get();
            if (passwordEncoder.matches(request.getPassword(), user.getPassword())){
                return new LoginResponse("Login Sucessful", "dummy-token");
            }
        }
        return new LoginResponse("Invalid username or password",null);

    }




    public User registerUser(String username, String email, String password) throws Exception {
        if (userRepository.findByUsername(username).isPresent()) {
            throw new Exception("username already taken");
        }
        if (userRepository.findByEmail(email).isPresent()) {
            throw new Exception("Email already taken");
        }
        String hashedPassword=passwordEncoder.encode(password);
        User user=new User();
        user.setUsername(username);
        user.setEmail(email);
        user.setPassword(hashedPassword);
        return userRepository.save(user);
    }

}
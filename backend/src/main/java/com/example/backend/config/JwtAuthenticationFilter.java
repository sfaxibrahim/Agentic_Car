package com.example.backend.security;

import com.example.backend.service.UserService;
import io.jsonwebtoken.JwtException;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtUtil jwtUtil;
    private final UserService userService;

    public JwtAuthenticationFilter(JwtUtil jwtUtil, UserService userService) {
        this.jwtUtil = jwtUtil;
        this.userService = userService;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain) throws ServletException, IOException {
        String header = request.getHeader("Authorization");
        if (header!=null && header.startsWith("Bearer")){
            String token =header.substring(7);
            try {
                String username= jwtUtil.extractUsername(token);
                UserDetails userDetails=userService.loadUserByUsername(username);
            }catch (JwtException e){
                // invalid token -> return 401 or let exception handler handle

            }
        }
        filterChain.doFilter(request,response);

    }
}

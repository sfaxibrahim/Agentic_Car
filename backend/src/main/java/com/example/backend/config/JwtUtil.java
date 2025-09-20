package com.example.backend.config;

import io.jsonwebtoken.*;

import io.jsonwebtoken.security.Keys;
import org.springframework.stereotype.Component;

import java.security.Key;
import java.util.Date;

@Component
public class JwtUtil {
    private final Key key = Keys.hmacShaKeyFor(System.getenv("JWT_SECRET").getBytes());

    public String generateAccessToken(String username, String roles){
        long expiry =1000*60*10;
        return Jwts.builder()
                .setSubject(username)
                .claim("roles",roles)
                .setIssuedAt(new Date())
                .setExpiration(new Date(System.currentTimeMillis()+expiry))
                .signWith(key)
                .compact();
    }
    public Jws<Claims> parseToken(String token){
        return Jwts.parserBuilder().setSigningKey(key).build().parseClaimsJws(token);
    }
    public String extractUsername(String token){
        return  parseToken(token).getBody().getSubject();
    }
}

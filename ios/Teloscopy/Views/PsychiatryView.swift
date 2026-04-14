// PsychiatryView.swift
// Teloscopy
//
// Counselling chat interface with TTS support.

import SwiftUI
import AVFoundation

struct PsychiatryView: View {
    @ObservedObject private var service = PsychiatryService.shared
    @State private var inputText = ""
    @State private var synthesizer = AVSpeechSynthesizer()
    @FocusState private var inputFocused: Bool
    
    var body: some View {
        VStack(spacing: 0) {
            // Header
            headerBar
            
            // Chat area
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 12) {
                        if service.messages.isEmpty {
                            welcomeCard
                        }
                        
                        ForEach(service.messages) { msg in
                            chatBubble(msg)
                                .id(msg.id)
                        }
                        
                        if service.isLoading {
                            typingIndicator
                                .id("typing")
                        }
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                }
                .onChange(of: service.messages.count) { _ in
                    withAnimation {
                        if let last = service.messages.last {
                            proxy.scrollTo(last.id, anchor: .bottom)
                        } else if service.isLoading {
                            proxy.scrollTo("typing", anchor: .bottom)
                        }
                    }
                }
            }
            
            // Error banner
            if let error = service.error {
                HStack {
                    Text(error)
                        .font(.caption)
                        .foregroundColor(.white)
                    Spacer()
                    Button("Dismiss") { service.clearError() }
                        .font(.caption.bold())
                        .foregroundColor(.white)
                }
                .padding(8)
                .background(Color.red.opacity(0.8))
            }
            
            // Input bar
            inputBar
        }
        .background(Color(red: 0.051, green: 0.063, blue: 0.118))
        .task {
            await service.loadThemes()
        }
    }
    
    // MARK: - Header
    
    private var headerBar: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text("Counselling")
                    .font(.headline)
                    .foregroundColor(.white)
                if !service.currentTheme.isEmpty {
                    let title = service.themes[service.currentTheme]?.title ?? service.currentTheme
                    Text(title)
                        .font(.caption)
                        .foregroundColor(Color(red: 0.4, green: 0.8, blue: 0.7))
                }
            }
            Spacer()
            if !service.messages.isEmpty {
                Button(action: {
                    synthesizer.stopSpeaking(at: .immediate)
                    service.clearChat()
                }) {
                    Image(systemName: "trash")
                        .foregroundColor(.gray)
                }
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(Color(red: 0.067, green: 0.082, blue: 0.157))
    }
    
    // MARK: - Welcome
    
    private var welcomeCard: some View {
        VStack(spacing: 16) {
            Spacer().frame(height: 24)
            
            ZStack {
                Circle()
                    .fill(
                        LinearGradient(
                            colors: [Color(red: 0.2, green: 0.5, blue: 1.0), Color(red: 0.4, green: 0.8, blue: 0.7)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 72, height: 72)
                Text("🧠")
                    .font(.system(size: 32))
            }
            
            Text("Reflective Counselling")
                .font(.title2.bold())
                .foregroundColor(.white)
            
            Text("A safe space for self-reflection through inquiry-based dialogue.\nThis is not a substitute for professional therapy.")
                .font(.subheadline)
                .foregroundColor(.gray)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 24)
            
            Text("Try saying: \"I've been feeling overwhelmed lately\"")
                .font(.caption)
                .italic()
                .foregroundColor(Color(red: 0.2, green: 0.5, blue: 1.0).opacity(0.8))
            
            Spacer().frame(height: 24)
        }
    }
    
    // MARK: - Chat Bubble
    
    @ViewBuilder
    private func chatBubble(_ message: PsychiatryService.ChatMessage) -> some View {
        let isUser = message.role == "user"
        
        VStack(alignment: isUser ? .trailing : .leading, spacing: 6) {
            HStack {
                if isUser { Spacer(minLength: 60) }
                
                VStack(alignment: .leading, spacing: 4) {
                    if !isUser {
                        Text("Counsellor")
                            .font(.caption2.bold())
                            .foregroundColor(Color(red: 0.4, green: 0.8, blue: 0.7))
                    }
                    
                    Text(message.text)
                        .font(.subheadline)
                        .foregroundColor(.white)
                        .lineSpacing(4)
                    
                    if !isUser {
                        Button(action: { speakText(message.text) }) {
                            Image(systemName: "speaker.wave.2")
                                .font(.caption)
                                .foregroundColor(.gray)
                        }
                    }
                }
                .padding(12)
                .background(
                    RoundedRectangle(cornerRadius: 16)
                        .fill(isUser
                              ? Color(red: 0.2, green: 0.5, blue: 1.0).opacity(0.15)
                              : Color(red: 0.067, green: 0.082, blue: 0.157))
                )
                
                if !isUser { Spacer(minLength: 60) }
            }
            
            // Follow-up chips
            if !isUser && !message.followups.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 6) {
                        ForEach(message.followups, id: \.self) { followup in
                            Button(action: {
                                Task { await service.sendMessage(followup) }
                            }) {
                                Text(followup)
                                    .font(.caption)
                                    .foregroundColor(Color(red: 0.2, green: 0.5, blue: 1.0))
                                    .padding(.horizontal, 10)
                                    .padding(.vertical, 6)
                                    .background(
                                        RoundedRectangle(cornerRadius: 12)
                                            .stroke(Color(red: 0.2, green: 0.5, blue: 1.0).opacity(0.3))
                                    )
                            }
                        }
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: isUser ? .trailing : .leading)
    }
    
    // MARK: - Typing Indicator
    
    private var typingIndicator: some View {
        HStack(spacing: 8) {
            Text("Counsellor")
                .font(.caption2.bold())
                .foregroundColor(Color(red: 0.4, green: 0.8, blue: 0.7))
            ProgressView()
                .scaleEffect(0.7)
                .tint(Color(red: 0.4, green: 0.8, blue: 0.7))
            Text("Reflecting…")
                .font(.caption)
                .italic()
                .foregroundColor(.gray)
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color(red: 0.067, green: 0.082, blue: 0.157))
        )
        .frame(maxWidth: .infinity, alignment: .leading)
    }
    
    // MARK: - Input Bar
    
    private var inputBar: some View {
        HStack(spacing: 8) {
            TextField("Share what's on your mind…", text: $inputText, axis: .vertical)
                .textFieldStyle(.plain)
                .foregroundColor(.white)
                .padding(10)
                .background(
                    RoundedRectangle(cornerRadius: 20)
                        .stroke(Color.gray.opacity(0.3))
                        .background(
                            RoundedRectangle(cornerRadius: 20)
                                .fill(Color(red: 0.051, green: 0.063, blue: 0.118))
                        )
                )
                .lineLimit(1...4)
                .focused($inputFocused)
                .disabled(service.isLoading)
            
            Button(action: {
                let text = inputText
                inputText = ""
                inputFocused = false
                Task { await service.sendMessage(text) }
            }) {
                ZStack {
                    Circle()
                        .fill(inputText.trimmingCharacters(in: .whitespaces).isEmpty
                              ? Color(red: 0.2, green: 0.5, blue: 1.0).opacity(0.3)
                              : Color(red: 0.2, green: 0.5, blue: 1.0))
                        .frame(width: 44, height: 44)
                    
                    if service.isLoading {
                        ProgressView()
                            .scaleEffect(0.8)
                            .tint(.white)
                    } else {
                        Image(systemName: "arrow.up")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundColor(.white)
                    }
                }
            }
            .disabled(inputText.trimmingCharacters(in: .whitespaces).isEmpty || service.isLoading)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(Color(red: 0.067, green: 0.082, blue: 0.157))
    }
    
    // MARK: - TTS
    
    private func speakText(_ text: String) {
        synthesizer.stopSpeaking(at: .immediate)
        let utterance = AVSpeechUtterance(string: text)
        utterance.voice = AVSpeechSynthesisVoice(language: "en-GB")
        utterance.rate = 0.48  // iOS rate scale is different (0.0-1.0, default 0.5)
        utterance.pitchMultiplier = 0.95
        utterance.volume = 0.9
        synthesizer.speak(utterance)
    }
}

#Preview {
    PsychiatryView()
}

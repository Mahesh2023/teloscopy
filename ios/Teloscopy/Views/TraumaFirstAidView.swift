// TraumaFirstAidView.swift
// Teloscopy
//
// Trauma response first aid sheet with crisis lines, grounding exercises,
// safety planning, de-escalation guidance, and psychoeducation.

import SwiftUI
import Combine

// MARK: - Color Constants

private let traumaBg = Color(red: 0.059, green: 0.039, blue: 0.078)
private let traumaSurface = Color(red: 0.102, green: 0.071, blue: 0.125)
private let traumaCoral = Color(red: 1.0, green: 0.42, blue: 0.42)
private let traumaAmber = Color(red: 1.0, green: 0.655, blue: 0.149)
private let traumaText = Color(red: 0.878, green: 0.855, blue: 0.910)
private let traumaTextSecondary = Color(red: 0.588, green: 0.557, blue: 0.647)

// MARK: - Tab Definition

private enum TraumaTab: Int, CaseIterable {
    case crisisLines = 0
    case grounding = 1
    case safetyPlan = 2
    case deescalation = 3
    case learn = 4

    var title: String {
        switch self {
        case .crisisLines: return "Crisis"
        case .grounding: return "Ground"
        case .safetyPlan: return "Safety"
        case .deescalation: return "De-escalate"
        case .learn: return "Learn"
        }
    }

    var icon: String {
        switch self {
        case .crisisLines: return "phone.fill"
        case .grounding: return "leaf.fill"
        case .safetyPlan: return "shield.fill"
        case .deescalation: return "hand.raised.fill"
        case .learn: return "book.fill"
        }
    }
}

// MARK: - Main View

struct TraumaFirstAidView: View {
    @State private var selectedTab = 0
    var crisisSeverity: String? = nil
    @Environment(\.openURL) var openURL
    @Environment(\.dismiss) var dismiss

    // Grounding state
    @State private var groundingStep = 0
    @State private var breathPhase = 0
    @State private var isBreathing = false
    @State private var countdown = 4
    @State private var cycleCount = 0
    @State private var breathTimer: AnyCancellable? = nil

    // Safety plan state
    @AppStorage("trauma_safety_plan_step_1") private var safetyStep1 = ""
    @AppStorage("trauma_safety_plan_step_2") private var safetyStep2 = ""
    @AppStorage("trauma_safety_plan_step_3") private var safetyStep3 = ""
    @AppStorage("trauma_safety_plan_step_4") private var safetyStep4 = ""
    @AppStorage("trauma_safety_plan_step_5") private var safetyStep5 = ""
    @AppStorage("trauma_safety_plan_step_6") private var safetyStep6 = ""
    @State private var showSaveConfirmation = false
    @State private var expandedSafetyStep: Int? = nil

    var body: some View {
        ZStack {
            traumaBg.ignoresSafeArea()

            VStack(spacing: 0) {
                headerBar
                tabSelector
                tabContent
            }
        }
        .onAppear {
            if crisisSeverity == "high" {
                selectedTab = 0
            }
        }
    }

    // MARK: - Header

    private var headerBar: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text("Trauma First Aid")
                    .font(.system(size: 20, weight: .bold))
                    .foregroundColor(traumaCoral)
                Text("Evidence-based crisis support")
                    .font(.system(size: 12, weight: .regular))
                    .foregroundColor(traumaTextSecondary)
            }
            Spacer()
            Button(action: { dismiss() }) {
                Image(systemName: "xmark.circle.fill")
                    .font(.system(size: 24))
                    .foregroundColor(traumaTextSecondary)
            }
        }
        .padding(.horizontal, 16)
        .padding(.top, 16)
        .padding(.bottom, 8)
    }

    // MARK: - Tab Selector

    private var tabSelector: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 6) {
                ForEach(TraumaTab.allCases, id: \.rawValue) { tab in
                    Button(action: {
                        withAnimation(.easeInOut(duration: 0.2)) {
                            selectedTab = tab.rawValue
                        }
                    }) {
                        HStack(spacing: 5) {
                            Image(systemName: tab.icon)
                                .font(.system(size: 12, weight: .semibold))
                            Text(tab.title)
                                .font(.system(size: 12, weight: .semibold))
                        }
                        .padding(.horizontal, 12)
                        .padding(.vertical, 8)
                        .background(
                            RoundedRectangle(cornerRadius: 10)
                                .fill(selectedTab == tab.rawValue
                                      ? traumaCoral.opacity(0.2)
                                      : traumaSurface)
                        )
                        .overlay(
                            RoundedRectangle(cornerRadius: 10)
                                .stroke(selectedTab == tab.rawValue
                                        ? traumaCoral.opacity(0.6)
                                        : Color.clear, lineWidth: 1)
                        )
                        .foregroundColor(selectedTab == tab.rawValue
                                         ? traumaCoral
                                         : traumaTextSecondary)
                    }
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
        }
    }

    // MARK: - Tab Content

    @ViewBuilder
    private var tabContent: some View {
        switch selectedTab {
        case 0: crisisLinesTab
        case 1: groundingTab
        case 2: safetyPlanTab
        case 3: deescalationTab
        case 4: learnTab
        default: crisisLinesTab
        }
    }

    // MARK: - Tab 1: Crisis Lines

    private var crisisLinesTab: some View {
        ScrollView {
            VStack(spacing: 12) {
                // Emergency 911
                Button(action: { if let url = URL(string: "tel:911") { openURL(url) } }) {
                    HStack(spacing: 12) {
                        ZStack {
                            Circle()
                                .fill(Color.red)
                                .frame(width: 44, height: 44)
                            Image(systemName: "exclamationmark.triangle.fill")
                                .font(.system(size: 18, weight: .bold))
                                .foregroundColor(.white)
                        }
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Emergency Services")
                                .font(.system(size: 16, weight: .bold))
                                .foregroundColor(.white)
                            Text("911")
                                .font(.system(size: 22, weight: .heavy, design: .monospaced))
                                .foregroundColor(traumaCoral)
                            Text("Immediate danger to life")
                                .font(.system(size: 12))
                                .foregroundColor(traumaTextSecondary)
                        }
                        Spacer()
                        Image(systemName: "phone.arrow.up.right.fill")
                            .font(.system(size: 20))
                            .foregroundColor(Color.red)
                    }
                    .padding(16)
                    .background(
                        RoundedRectangle(cornerRadius: 16)
                            .fill(Color.red.opacity(0.12))
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 16)
                            .stroke(Color.red.opacity(0.4), lineWidth: 1.5)
                    )
                }

                // Hotline cards
                ForEach(crisisHotlines, id: \.name) { hotline in
                    crisisCard(hotline: hotline)
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
    }

    private func crisisCard(hotline: CrisisHotline) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text(hotline.name)
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundColor(traumaText)
                Spacer()
                Text(hotline.hours)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundColor(traumaAmber)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(
                        Capsule().fill(traumaAmber.opacity(0.12))
                    )
            }

            Text(hotline.number)
                .font(.system(size: 20, weight: .bold, design: .monospaced))
                .foregroundColor(traumaCoral)

            Text(hotline.description)
                .font(.system(size: 13))
                .foregroundColor(traumaTextSecondary)
                .lineLimit(2)

            HStack(spacing: 10) {
                Button(action: {
                    if let url = URL(string: "tel:\(hotline.number.replacingOccurrences(of: "-", with: "").replacingOccurrences(of: " ", with: ""))") {
                        openURL(url)
                    }
                }) {
                    HStack(spacing: 6) {
                        Image(systemName: "phone.fill")
                            .font(.system(size: 13))
                        Text("Call")
                            .font(.system(size: 13, weight: .semibold))
                    }
                    .foregroundColor(.white)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 8)
                    .background(
                        Capsule().fill(traumaCoral)
                    )
                }

                if let sms = hotline.smsNumber {
                    Button(action: {
                        if let url = URL(string: "sms:\(sms.replacingOccurrences(of: "-", with: ""))") {
                            openURL(url)
                        }
                    }) {
                        HStack(spacing: 6) {
                            Image(systemName: "message.fill")
                                .font(.system(size: 13))
                            Text("Text")
                                .font(.system(size: 13, weight: .semibold))
                        }
                        .foregroundColor(traumaCoral)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 8)
                        .background(
                            Capsule().stroke(traumaCoral, lineWidth: 1)
                        )
                    }
                }
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(traumaSurface)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(traumaCoral.opacity(0.2), lineWidth: 1)
        )
        .shadow(color: traumaCoral.opacity(0.1), radius: 8)
    }

    // MARK: - Tab 2: Grounding

    private var groundingTab: some View {
        ScrollView {
            VStack(spacing: 20) {
                groundingExercise
                boxBreathingSection
                butterflyHugCard
                bodyScanCard
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
    }

    // MARK: 5-4-3-2-1 Grounding

    private var groundingExercise: some View {
        let steps: [(count: Int, sense: String, instruction: String, examples: String, color: Color)] = [
            (5, "See", "Name 5 things you can see right now", "Wall, ceiling, hands, phone, window", Color.red),
            (4, "Touch", "Name 4 things you can touch", "Chair, fabric, skin, table surface", Color.orange),
            (3, "Hear", "Name 3 things you can hear", "Breathing, traffic, clock ticking", Color.green),
            (2, "Smell", "Name 2 things you can smell", "Air, soap, food, fabric softener", Color.blue),
            (1, "Taste", "Name 1 thing you can taste", "Water, toothpaste, coffee, gum", Color.purple)
        ]

        return VStack(spacing: 12) {
            sectionHeader(title: "5-4-3-2-1 Grounding", icon: "hand.point.up.braille.fill")

            if groundingStep < steps.count {
                let step = steps[groundingStep]
                VStack(spacing: 16) {
                    ZStack {
                        Circle()
                            .fill(step.color.opacity(0.15))
                            .frame(width: 72, height: 72)
                        Text("\(step.count)")
                            .font(.system(size: 32, weight: .heavy))
                            .foregroundColor(step.color)
                    }

                    Text(step.sense)
                        .font(.system(size: 20, weight: .bold))
                        .foregroundColor(step.color)

                    Text(step.instruction)
                        .font(.system(size: 15))
                        .foregroundColor(traumaText)
                        .multilineTextAlignment(.center)

                    Text("Examples: \(step.examples)")
                        .font(.system(size: 12, weight: .medium))
                        .foregroundColor(traumaTextSecondary)
                        .italic()
                        .multilineTextAlignment(.center)

                    HStack(spacing: 12) {
                        if groundingStep > 0 {
                            Button(action: { withAnimation { groundingStep -= 1 } }) {
                                Text("Back")
                                    .font(.system(size: 14, weight: .semibold))
                                    .foregroundColor(traumaTextSecondary)
                                    .padding(.horizontal, 24)
                                    .padding(.vertical, 10)
                                    .background(
                                        Capsule().stroke(traumaTextSecondary, lineWidth: 1)
                                    )
                            }
                        }
                        Button(action: { withAnimation { groundingStep += 1 } }) {
                            Text(groundingStep < steps.count - 1 ? "Next" : "Finish")
                                .font(.system(size: 14, weight: .semibold))
                                .foregroundColor(.white)
                                .padding(.horizontal, 24)
                                .padding(.vertical, 10)
                                .background(
                                    Capsule().fill(step.color)
                                )
                        }
                    }

                    // Progress dots
                    HStack(spacing: 6) {
                        ForEach(0..<steps.count, id: \.self) { i in
                            Circle()
                                .fill(i <= groundingStep ? steps[i].color : traumaTextSecondary.opacity(0.3))
                                .frame(width: 8, height: 8)
                        }
                    }
                }
                .padding(20)
                .background(
                    RoundedRectangle(cornerRadius: 16)
                        .fill(traumaSurface)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(step.color.opacity(0.3), lineWidth: 1)
                )
            } else {
                VStack(spacing: 12) {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 40))
                        .foregroundColor(Color.green)
                    Text("Grounding Complete")
                        .font(.system(size: 18, weight: .bold))
                        .foregroundColor(traumaText)
                    Text("You've reconnected with the present moment.")
                        .font(.system(size: 14))
                        .foregroundColor(traumaTextSecondary)
                        .multilineTextAlignment(.center)
                    Button(action: { withAnimation { groundingStep = 0 } }) {
                        Text("Reset")
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundColor(traumaCoral)
                            .padding(.horizontal, 24)
                            .padding(.vertical, 10)
                            .background(
                                Capsule().stroke(traumaCoral, lineWidth: 1)
                            )
                    }
                }
                .padding(20)
                .background(
                    RoundedRectangle(cornerRadius: 16).fill(traumaSurface)
                )
            }
        }
    }

    // MARK: Box Breathing

    private var boxBreathingSection: some View {
        let phaseLabels = ["Breathe In", "Hold", "Breathe Out", "Hold"]
        let phaseColors: [Color] = [Color.blue, traumaAmber, Color.green, traumaAmber]

        return VStack(spacing: 12) {
            sectionHeader(title: "Box Breathing", icon: "wind")

            VStack(spacing: 20) {
                ZStack {
                    Circle()
                        .stroke(phaseColors[breathPhase].opacity(0.2), lineWidth: 3)
                        .frame(width: 120, height: 120)
                    Circle()
                        .fill(phaseColors[breathPhase].opacity(0.15))
                        .frame(width: isBreathing ? 120 : 60, height: isBreathing ? 120 : 60)
                        .scaleEffect(breathPhase == 0 || breathPhase == 1 ? 1.0 : 0.6)
                        .animation(.easeInOut(duration: 1), value: breathPhase)
                    VStack(spacing: 4) {
                        Text("\(countdown)")
                            .font(.system(size: 32, weight: .heavy, design: .monospaced))
                            .foregroundColor(phaseColors[breathPhase])
                        Text(isBreathing ? phaseLabels[breathPhase] : "Ready")
                            .font(.system(size: 13, weight: .semibold))
                            .foregroundColor(traumaText)
                    }
                }

                if isBreathing {
                    Text("Cycle \(cycleCount + 1)")
                        .font(.system(size: 12, weight: .medium))
                        .foregroundColor(traumaTextSecondary)
                }

                Button(action: { toggleBreathing() }) {
                    HStack(spacing: 8) {
                        Image(systemName: isBreathing ? "stop.fill" : "play.fill")
                            .font(.system(size: 14))
                        Text(isBreathing ? "Stop" : "Start")
                            .font(.system(size: 15, weight: .semibold))
                    }
                    .foregroundColor(.white)
                    .padding(.horizontal, 32)
                    .padding(.vertical, 12)
                    .background(
                        Capsule().fill(isBreathing ? Color.red.opacity(0.8) : traumaCoral)
                    )
                }

                Text("Breathe in for 4s, hold for 4s, breathe out for 4s, hold for 4s. Repeat to calm the nervous system.")
                    .font(.system(size: 12))
                    .foregroundColor(traumaTextSecondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 8)
            }
            .padding(20)
            .background(
                RoundedRectangle(cornerRadius: 16).fill(traumaSurface)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 16)
                    .stroke(traumaCoral.opacity(0.2), lineWidth: 1)
            )
            .shadow(color: traumaCoral.opacity(0.1), radius: 8)
            .onReceive(Timer.publish(every: 1, on: .main, in: .common).autoconnect()) { _ in
                guard isBreathing else { return }
                if countdown > 1 {
                    countdown -= 1
                } else {
                    let nextPhase = (breathPhase + 1) % 4
                    if nextPhase == 0 { cycleCount += 1 }
                    withAnimation(.easeInOut(duration: 1)) {
                        breathPhase = nextPhase
                    }
                    countdown = 4
                }
            }
        }
    }

    private func toggleBreathing() {
        if isBreathing {
            isBreathing = false
            breathPhase = 0
            countdown = 4
            cycleCount = 0
        } else {
            isBreathing = true
            breathPhase = 0
            countdown = 4
            cycleCount = 0
        }
    }

    // MARK: Butterfly Hug

    private var butterflyHugCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            sectionHeader(title: "Butterfly Hug", icon: "hands.sparkles.fill")

            VStack(alignment: .leading, spacing: 8) {
                instructionRow(number: "1", text: "Cross your arms over your chest, fingers touching below collarbones")
                instructionRow(number: "2", text: "Alternately tap your hands slowly, like butterfly wings")
                instructionRow(number: "3", text: "Focus on a calm or neutral thought while tapping")
                instructionRow(number: "4", text: "Continue for 1-2 minutes at a comfortable pace")
            }
            .padding(16)
            .background(
                RoundedRectangle(cornerRadius: 16).fill(traumaSurface)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 16)
                    .stroke(traumaCoral.opacity(0.2), lineWidth: 1)
            )
        }
    }

    // MARK: Body Scan

    private var bodyScanCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            sectionHeader(title: "Quick Body Scan", icon: "figure.mind.and.body")

            VStack(alignment: .leading, spacing: 8) {
                instructionRow(number: "1", text: "Sit or lie comfortably. Close your eyes if it feels safe.")
                instructionRow(number: "2", text: "Notice your feet on the ground. Feel the contact.")
                instructionRow(number: "3", text: "Slowly move attention up: legs, hips, belly, chest.")
                instructionRow(number: "4", text: "Notice any tension without judgment. Breathe into it.")
                instructionRow(number: "5", text: "Continue to shoulders, neck, face. Soften each area.")
            }
            .padding(16)
            .background(
                RoundedRectangle(cornerRadius: 16).fill(traumaSurface)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 16)
                    .stroke(traumaCoral.opacity(0.2), lineWidth: 1)
            )
        }
    }

    // MARK: - Tab 3: Safety Plan

    private var safetyPlanTab: some View {
        ScrollView {
            VStack(spacing: 12) {
                Text("Your Personal Safety Plan")
                    .font(.system(size: 18, weight: .bold))
                    .foregroundColor(traumaAmber)
                    .frame(maxWidth: .infinity, alignment: .leading)

                Text("Saved securely on your device. Complete each step when you feel ready.")
                    .font(.system(size: 13))
                    .foregroundColor(traumaTextSecondary)
                    .frame(maxWidth: .infinity, alignment: .leading)

                safetyPlanStep(
                    step: 1,
                    title: "Warning Signs",
                    prompt: "What thoughts, feelings, or behaviors tell you a crisis may be developing?",
                    examples: ["Racing thoughts", "Withdrawing", "Not sleeping", "Irritability"],
                    binding: $safetyStep1
                )
                safetyPlanStep(
                    step: 2,
                    title: "Internal Coping Strategies",
                    prompt: "Things I can do on my own to take my mind off problems:",
                    examples: ["Go for a walk", "Listen to music", "Deep breathing", "Journal"],
                    binding: $safetyStep2
                )
                safetyPlanStep(
                    step: 3,
                    title: "People & Places for Distraction",
                    prompt: "People and social settings that provide distraction:",
                    examples: ["Coffee shop", "Friend's house", "Library", "Park"],
                    binding: $safetyStep3
                )
                safetyPlanStep(
                    step: 4,
                    title: "People I Can Ask for Help",
                    prompt: "People I can contact when I need support:",
                    examples: ["Family member", "Close friend", "Therapist", "Mentor"],
                    binding: $safetyStep4
                )
                safetyPlanStep(
                    step: 5,
                    title: "Professionals & Agencies",
                    prompt: "Professional contacts and crisis services I can reach out to:",
                    examples: ["Therapist", "988 Lifeline", "Crisis Text Line", "Local ER"],
                    binding: $safetyStep5
                )
                safetyPlanStep(
                    step: 6,
                    title: "Making the Environment Safe",
                    prompt: "Steps I can take to reduce access to means and create safety:",
                    examples: ["Remove items", "Stay with someone", "Lock away medications", "Go to safe place"],
                    binding: $safetyStep6
                )

                if showSaveConfirmation {
                    HStack(spacing: 8) {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundColor(Color.green)
                        Text("Safety plan saved to device")
                            .font(.system(size: 13, weight: .medium))
                            .foregroundColor(Color.green)
                    }
                    .padding(12)
                    .background(
                        RoundedRectangle(cornerRadius: 10)
                            .fill(Color.green.opacity(0.1))
                    )
                    .transition(.opacity)
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
    }

    private func safetyPlanStep(
        step: Int,
        title: String,
        prompt: String,
        examples: [String],
        binding: Binding<String>
    ) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            DisclosureGroup(
                isExpanded: Binding(
                    get: { expandedSafetyStep == step },
                    set: { expandedSafetyStep = $0 ? step : nil }
                )
            ) {
                VStack(alignment: .leading, spacing: 10) {
                    Text(prompt)
                        .font(.system(size: 13))
                        .foregroundColor(traumaTextSecondary)
                        .padding(.top, 8)

                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 6) {
                            ForEach(examples, id: \.self) { example in
                                Text(example)
                                    .font(.system(size: 11, weight: .medium))
                                    .foregroundColor(traumaAmber)
                                    .padding(.horizontal, 10)
                                    .padding(.vertical, 5)
                                    .background(
                                        Capsule().fill(traumaAmber.opacity(0.1))
                                    )
                                    .overlay(
                                        Capsule().stroke(traumaAmber.opacity(0.3), lineWidth: 0.5)
                                    )
                            }
                        }
                    }

                    TextEditor(text: binding)
                        .font(.system(size: 14))
                        .foregroundColor(traumaText)
                        .scrollContentBackground(.hidden)
                        .frame(minHeight: 80)
                        .padding(10)
                        .background(
                            RoundedRectangle(cornerRadius: 10)
                                .fill(traumaBg)
                        )
                        .overlay(
                            RoundedRectangle(cornerRadius: 10)
                                .stroke(traumaCoral.opacity(0.15), lineWidth: 1)
                        )

                    Button(action: {
                        let generator = UINotificationFeedbackGenerator()
                        generator.notificationOccurred(.success)
                        withAnimation { showSaveConfirmation = true }
                        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                            withAnimation { showSaveConfirmation = false }
                        }
                    }) {
                        HStack(spacing: 6) {
                            Image(systemName: "square.and.arrow.down.fill")
                                .font(.system(size: 12))
                            Text("Save")
                                .font(.system(size: 13, weight: .semibold))
                        }
                        .foregroundColor(traumaCoral)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 8)
                        .background(
                            Capsule().stroke(traumaCoral, lineWidth: 1)
                        )
                    }
                    .padding(.top, 4)
                }
            } label: {
                HStack(spacing: 10) {
                    ZStack {
                        Circle()
                            .fill(traumaCoral.opacity(0.15))
                            .frame(width: 30, height: 30)
                        Text("\(step)")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundColor(traumaCoral)
                    }
                    Text(title)
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundColor(traumaText)
                    Spacer()
                    if !binding.wrappedValue.isEmpty {
                        Image(systemName: "checkmark.circle.fill")
                            .font(.system(size: 14))
                            .foregroundColor(Color.green)
                    }
                }
            }
            .accentColor(traumaTextSecondary)
        }
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: 16).fill(traumaSurface)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(traumaCoral.opacity(0.2), lineWidth: 1)
        )
        .shadow(color: traumaCoral.opacity(0.1), radius: 8)
    }

    // MARK: - Tab 4: De-escalation

    private var deescalationTab: some View {
        ScrollView {
            VStack(spacing: 16) {
                // LEAP Method
                sectionHeader(title: "LEAP Method", icon: "person.2.fill")

                ForEach(leapSteps, id: \.letter) { step in
                    HStack(alignment: .top, spacing: 14) {
                        ZStack {
                            RoundedRectangle(cornerRadius: 10)
                                .fill(traumaCoral.opacity(0.15))
                                .frame(width: 44, height: 44)
                            Text(step.letter)
                                .font(.system(size: 22, weight: .heavy))
                                .foregroundColor(traumaCoral)
                        }
                        VStack(alignment: .leading, spacing: 4) {
                            Text(step.word)
                                .font(.system(size: 16, weight: .bold))
                                .foregroundColor(traumaAmber)
                            Text(step.description)
                                .font(.system(size: 13))
                                .foregroundColor(traumaTextSecondary)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                    .padding(14)
                    .background(
                        RoundedRectangle(cornerRadius: 16).fill(traumaSurface)
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 16)
                            .stroke(traumaCoral.opacity(0.2), lineWidth: 1)
                    )
                }

                // Do's
                sectionHeader(title: "Do's", icon: "checkmark.seal.fill")

                VStack(alignment: .leading, spacing: 10) {
                    ForEach(deescalationDos, id: \.self) { item in
                        HStack(alignment: .top, spacing: 10) {
                            Image(systemName: "checkmark.circle.fill")
                                .font(.system(size: 16))
                                .foregroundColor(Color.green)
                            Text(item)
                                .font(.system(size: 14))
                                .foregroundColor(traumaText)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }
                .padding(16)
                .background(
                    RoundedRectangle(cornerRadius: 16).fill(traumaSurface)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(Color.green.opacity(0.2), lineWidth: 1)
                )

                // Don'ts
                sectionHeader(title: "Don'ts", icon: "xmark.seal.fill")

                VStack(alignment: .leading, spacing: 10) {
                    ForEach(deescalationDonts, id: \.self) { item in
                        HStack(alignment: .top, spacing: 10) {
                            Image(systemName: "xmark.circle.fill")
                                .font(.system(size: 16))
                                .foregroundColor(Color.red)
                            Text(item)
                                .font(.system(size: 14))
                                .foregroundColor(traumaText)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }
                .padding(16)
                .background(
                    RoundedRectangle(cornerRadius: 16).fill(traumaSurface)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(Color.red.opacity(0.2), lineWidth: 1)
                )

                // When to Call 911
                VStack(alignment: .leading, spacing: 10) {
                    HStack(spacing: 8) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .font(.system(size: 16))
                            .foregroundColor(Color.red)
                        Text("When to Call 911")
                            .font(.system(size: 16, weight: .bold))
                            .foregroundColor(Color.red)
                    }

                    ForEach(call911Reasons, id: \.self) { reason in
                        HStack(alignment: .top, spacing: 8) {
                            Circle()
                                .fill(Color.red)
                                .frame(width: 6, height: 6)
                                .padding(.top, 6)
                            Text(reason)
                                .font(.system(size: 13))
                                .foregroundColor(traumaText)
                        }
                    }

                    Button(action: { if let url = URL(string: "tel:911") { openURL(url) } }) {
                        HStack(spacing: 8) {
                            Image(systemName: "phone.fill")
                            Text("Call 911")
                                .font(.system(size: 15, weight: .bold))
                        }
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(
                            RoundedRectangle(cornerRadius: 12).fill(Color.red)
                        )
                    }
                    .padding(.top, 4)
                }
                .padding(16)
                .background(
                    RoundedRectangle(cornerRadius: 16)
                        .fill(Color.red.opacity(0.08))
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(Color.red.opacity(0.4), lineWidth: 1.5)
                )
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
    }

    // MARK: - Tab 5: Learn

    private var learnTab: some View {
        ScrollView {
            VStack(spacing: 16) {
                // Common Trauma Responses
                sectionHeader(title: "Common Trauma Responses", icon: "brain.head.profile")

                ForEach(traumaResponseCategories, id: \.category) { category in
                    VStack(alignment: .leading, spacing: 8) {
                        Text(category.category)
                            .font(.system(size: 15, weight: .bold))
                            .foregroundColor(traumaAmber)

                        ForEach(category.responses, id: \.self) { response in
                            HStack(alignment: .top, spacing: 8) {
                                Circle()
                                    .fill(traumaCoral.opacity(0.6))
                                    .frame(width: 5, height: 5)
                                    .padding(.top, 6)
                                Text(response)
                                    .font(.system(size: 13))
                                    .foregroundColor(traumaText)
                            }
                        }
                    }
                    .padding(14)
                    .background(
                        RoundedRectangle(cornerRadius: 16).fill(traumaSurface)
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 16)
                            .stroke(traumaCoral.opacity(0.2), lineWidth: 1)
                    )
                }

                // SAMHSA 6 Principles
                sectionHeader(title: "SAMHSA's 6 Principles", icon: "list.bullet.clipboard.fill")

                VStack(alignment: .leading, spacing: 10) {
                    ForEach(samhsaPrinciples, id: \.title) { principle in
                        HStack(alignment: .top, spacing: 10) {
                            Image(systemName: "diamond.fill")
                                .font(.system(size: 8))
                                .foregroundColor(traumaAmber)
                                .padding(.top, 5)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(principle.title)
                                    .font(.system(size: 14, weight: .semibold))
                                    .foregroundColor(traumaText)
                                Text(principle.description)
                                    .font(.system(size: 12))
                                    .foregroundColor(traumaTextSecondary)
                            }
                        }
                    }
                }
                .padding(16)
                .background(
                    RoundedRectangle(cornerRadius: 16).fill(traumaSurface)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(traumaCoral.opacity(0.2), lineWidth: 1)
                )

                // When to Seek Help
                sectionHeader(title: "When to Seek Professional Help", icon: "heart.text.square.fill")

                VStack(alignment: .leading, spacing: 8) {
                    ForEach(seekHelpSigns, id: \.self) { sign in
                        HStack(alignment: .top, spacing: 10) {
                            Image(systemName: "arrow.right.circle.fill")
                                .font(.system(size: 14))
                                .foregroundColor(traumaAmber)
                            Text(sign)
                                .font(.system(size: 13))
                                .foregroundColor(traumaText)
                        }
                    }
                }
                .padding(16)
                .background(
                    RoundedRectangle(cornerRadius: 16).fill(traumaSurface)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(traumaAmber.opacity(0.3), lineWidth: 1)
                )

                // Harmful Practices
                sectionHeader(title: "Harmful Practices to Avoid", icon: "exclamationmark.octagon.fill")

                VStack(alignment: .leading, spacing: 8) {
                    ForEach(harmfulPractices, id: \.self) { practice in
                        HStack(alignment: .top, spacing: 10) {
                            Image(systemName: "xmark.circle.fill")
                                .font(.system(size: 14))
                                .foregroundColor(Color.red.opacity(0.8))
                            Text(practice)
                                .font(.system(size: 13))
                                .foregroundColor(traumaText)
                        }
                    }
                }
                .padding(16)
                .background(
                    RoundedRectangle(cornerRadius: 16).fill(traumaSurface)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(Color.red.opacity(0.2), lineWidth: 1)
                )

                // PFA Overview
                sectionHeader(title: "Psychological First Aid (PFA)", icon: "cross.circle.fill")

                VStack(alignment: .leading, spacing: 14) {
                    Text("The Look-Listen-Link model provides a framework for immediate support:")
                        .font(.system(size: 13))
                        .foregroundColor(traumaTextSecondary)

                    ForEach(pfaSteps, id: \.title) { step in
                        HStack(alignment: .top, spacing: 12) {
                            ZStack {
                                Circle()
                                    .fill(traumaCoral.opacity(0.15))
                                    .frame(width: 36, height: 36)
                                Image(systemName: step.icon)
                                    .font(.system(size: 16))
                                    .foregroundColor(traumaCoral)
                            }
                            VStack(alignment: .leading, spacing: 3) {
                                Text(step.title)
                                    .font(.system(size: 15, weight: .bold))
                                    .foregroundColor(traumaAmber)
                                Text(step.description)
                                    .font(.system(size: 13))
                                    .foregroundColor(traumaText)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                        }
                    }
                }
                .padding(16)
                .background(
                    RoundedRectangle(cornerRadius: 16).fill(traumaSurface)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(traumaCoral.opacity(0.2), lineWidth: 1)
                )
                .shadow(color: traumaCoral.opacity(0.1), radius: 8)

                // Disclaimer
                Text("This tool provides educational information only and is not a substitute for professional mental health care. If you are in crisis, please contact a crisis line or emergency services.")
                    .font(.system(size: 11))
                    .foregroundColor(traumaTextSecondary.opacity(0.7))
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 8)
                    .padding(.top, 8)
                    .padding(.bottom, 20)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
    }

    // MARK: - Helpers

    private func sectionHeader(title: String, icon: String) -> some View {
        HStack(spacing: 8) {
            Image(systemName: icon)
                .font(.system(size: 14, weight: .semibold))
                .foregroundColor(traumaAmber)
            Text(title)
                .font(.system(size: 16, weight: .bold))
                .foregroundColor(traumaAmber)
            Spacer()
        }
    }

    private func instructionRow(number: String, text: String) -> some View {
        HStack(alignment: .top, spacing: 10) {
            ZStack {
                Circle()
                    .fill(traumaCoral.opacity(0.12))
                    .frame(width: 24, height: 24)
                Text(number)
                    .font(.system(size: 12, weight: .bold))
                    .foregroundColor(traumaCoral)
            }
            Text(text)
                .font(.system(size: 13))
                .foregroundColor(traumaText)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

// MARK: - Data Models

private struct CrisisHotline {
    let name: String
    let number: String
    let description: String
    let hours: String
    let smsNumber: String?
    let smsBody: String?
}

private struct LEAPStep {
    let letter: String
    let word: String
    let description: String
}

private struct TraumaResponseCategory {
    let category: String
    let responses: [String]
}

private struct SAMHSAPrinciple {
    let title: String
    let description: String
}

private struct PFAStep {
    let title: String
    let icon: String
    let description: String
}

// MARK: - Static Data

private let crisisHotlines: [CrisisHotline] = [
    CrisisHotline(
        name: "988 Suicide & Crisis Lifeline",
        number: "988",
        description: "Free, confidential 24/7 support for people in suicidal crisis or emotional distress.",
        hours: "24/7",
        smsNumber: "988",
        smsBody: "HELLO"
    ),
    CrisisHotline(
        name: "Crisis Text Line",
        number: "741741",
        description: "Text-based crisis support. Text HELLO to connect with a trained crisis counselor.",
        hours: "24/7",
        smsNumber: "741741",
        smsBody: "HELLO"
    ),
    CrisisHotline(
        name: "Veterans Crisis Line",
        number: "988",
        description: "Support for veterans and their families. Press 1 after dialing 988.",
        hours: "24/7",
        smsNumber: "838255",
        smsBody: nil
    ),
    CrisisHotline(
        name: "SAMHSA National Helpline",
        number: "1-800-662-4357",
        description: "Free referral and information service for substance abuse and mental health.",
        hours: "24/7",
        smsNumber: nil,
        smsBody: nil
    ),
    CrisisHotline(
        name: "National Domestic Violence Hotline",
        number: "1-800-799-7233",
        description: "Confidential support for anyone affected by domestic violence.",
        hours: "24/7",
        smsNumber: "88788",
        smsBody: "START"
    ),
    CrisisHotline(
        name: "RAINN Sexual Assault Hotline",
        number: "1-800-656-4673",
        description: "Connects to a local sexual assault service provider for confidential support.",
        hours: "24/7",
        smsNumber: nil,
        smsBody: nil
    ),
    CrisisHotline(
        name: "Trevor Project (LGBTQ+ Youth)",
        number: "1-866-488-7386",
        description: "Crisis intervention and suicide prevention for LGBTQ+ young people under 25.",
        hours: "24/7",
        smsNumber: "678-678",
        smsBody: "START"
    ),
    CrisisHotline(
        name: "iCall (India)",
        number: "9152987821",
        description: "Psychosocial helpline by TISS for emotional support and crisis intervention.",
        hours: "Mon-Sat 8am-10pm IST",
        smsNumber: nil,
        smsBody: nil
    ),
    CrisisHotline(
        name: "Vandrevala Foundation (India)",
        number: "1860-2662-345",
        description: "Mental health support helpline available across India. 24/7.",
        hours: "24/7",
        smsNumber: nil,
        smsBody: nil
    ),
    CrisisHotline(
        name: "Samaritans (UK/Ireland)",
        number: "116 123",
        description: "Emotional support for anyone in distress or at risk of suicide.",
        hours: "24/7",
        smsNumber: nil,
        smsBody: nil
    ),
    CrisisHotline(
        name: "Beyond Blue (Australia)",
        number: "1300 22 4636",
        description: "Support for anxiety, depression, and suicide prevention.",
        hours: "24/7",
        smsNumber: nil,
        smsBody: nil
    )
]

private let leapSteps: [LEAPStep] = [
    LEAPStep(
        letter: "L",
        word: "Listen",
        description: "Actively listen without interrupting. Reflect back what you hear. Show you are paying full attention with body language and verbal acknowledgments."
    ),
    LEAPStep(
        letter: "E",
        word: "Empathize",
        description: "Express genuine understanding of their emotions. Use phrases like \"That sounds really difficult\" or \"I can see why you feel that way.\" Validate without judgment."
    ),
    LEAPStep(
        letter: "A",
        word: "Agree",
        description: "Find common ground. Agree on shared goals even if you disagree on methods. Focus on what you both want: safety, relief, and a path forward."
    ),
    LEAPStep(
        letter: "P",
        word: "Partner",
        description: "Work together toward solutions. Offer choices rather than directives. Empower the person to be part of the decision-making process."
    )
]

private let deescalationDos: [String] = [
    "Speak slowly, calmly, and in a low tone of voice",
    "Use the person's name if you know it",
    "Acknowledge their feelings: \"I can see you're upset\"",
    "Give them space — maintain a safe physical distance",
    "Offer simple choices: \"Would you like to sit down or step outside?\"",
    "Be patient — allow silence and time to process",
    "Keep your body language open and non-threatening",
    "Focus on their immediate needs: water, quiet, comfort"
]

private let deescalationDonts: [String] = [
    "Don't argue, challenge, or try to \"win\" the conversation",
    "Don't raise your voice or match their intensity",
    "Don't make sudden movements or crowd their space",
    "Don't make promises you can't keep",
    "Don't take insults or anger personally",
    "Don't minimize their feelings: avoid \"calm down\" or \"it's not that bad\"",
    "Don't use authoritative commands or ultimatums"
]

private let call911Reasons: [String] = [
    "Person has a weapon or is threatening violence",
    "Someone is physically injured and needs medical attention",
    "Person is actively attempting self-harm",
    "You feel your own safety is at risk",
    "Person is experiencing a medical emergency (overdose, seizure)",
    "A child or vulnerable adult is in immediate danger"
]

private let traumaResponseCategories: [TraumaResponseCategory] = [
    TraumaResponseCategory(
        category: "Emotional",
        responses: ["Anxiety and fear", "Anger and irritability", "Sadness and grief", "Guilt or shame", "Emotional numbness", "Mood swings"]
    ),
    TraumaResponseCategory(
        category: "Physical",
        responses: ["Insomnia or nightmares", "Fatigue and exhaustion", "Headaches or body pain", "Rapid heartbeat", "Startle response", "Changes in appetite"]
    ),
    TraumaResponseCategory(
        category: "Cognitive",
        responses: ["Intrusive memories or flashbacks", "Difficulty concentrating", "Confusion or disorientation", "Negative self-talk", "Memory difficulties", "Hypervigilance"]
    ),
    TraumaResponseCategory(
        category: "Behavioral",
        responses: ["Social withdrawal", "Avoidance of reminders", "Increased substance use", "Changes in routine", "Difficulty with daily tasks", "Restlessness or agitation"]
    )
]

private let samhsaPrinciples: [SAMHSAPrinciple] = [
    SAMHSAPrinciple(title: "Safety", description: "Ensuring physical and emotional safety for all involved."),
    SAMHSAPrinciple(title: "Trustworthiness & Transparency", description: "Building trust through open communication and consistency."),
    SAMHSAPrinciple(title: "Peer Support", description: "Connecting with others who have shared experiences."),
    SAMHSAPrinciple(title: "Collaboration & Mutuality", description: "Sharing power and decision-making in healing."),
    SAMHSAPrinciple(title: "Empowerment & Choice", description: "Prioritizing individual strengths and self-determination."),
    SAMHSAPrinciple(title: "Cultural, Historical & Gender Issues", description: "Recognizing and addressing cultural contexts and biases.")
]

private let seekHelpSigns: [String] = [
    "Symptoms persist or worsen after 4+ weeks",
    "Difficulty functioning at work, school, or home",
    "Persistent nightmares or flashbacks",
    "Using alcohol or substances to cope",
    "Feeling constantly on edge or detached",
    "Thoughts of self-harm or harming others",
    "Inability to care for yourself or dependents",
    "Relationships are significantly impacted"
]

private let harmfulPractices: [String] = [
    "Forced debriefing immediately after trauma (Critical Incident Stress Debriefing)",
    "Pressuring someone to \"talk about it\" before they're ready",
    "Minimizing or comparing trauma: \"Others have it worse\"",
    "Using exposure to triggers without professional guidance",
    "Telling someone to \"just get over it\" or \"move on\"",
    "Isolating the person from their support network"
]

private let pfaSteps: [PFAStep] = [
    PFAStep(
        title: "Look",
        icon: "eye.fill",
        description: "Observe the situation for safety concerns, people with obvious urgent needs, and those showing signs of serious distress."
    ),
    PFAStep(
        title: "Listen",
        icon: "ear.fill",
        description: "Approach people who may need support. Ask about their needs and concerns. Listen actively and help them feel calm."
    ),
    PFAStep(
        title: "Link",
        icon: "link",
        description: "Help people address basic needs and access services. Connect them with loved ones and social support. Provide information about available resources."
    )
]

// MARK: - Preview

#Preview {
    TraumaFirstAidView()
        .preferredColorScheme(.dark)
}

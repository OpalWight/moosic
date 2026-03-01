import SwiftUI

struct PitchPoint: Identifiable {
    let id = UUID()
    let time: Double
    let frequency: Float
}

struct PitchCurveView: View {
    let targetHistory: [PitchPoint]
    let liveHistory: [PitchPoint]
    let currentTime: Double
    
    private let viewWidth: CGFloat = 800
    private let viewHeight: CGFloat = 200
    private let timeWindow: Double = 5.0 // Seconds to show
    
    var body: some View {
        ZStack {
            // Grid lines
            Path { path in
                for i in 0...4 {
                    let y = CGFloat(i) * (viewHeight / 4)
                    path.move(to: CGPoint(x: 0, y: y))
                    path.addLine(to: CGPoint(x: viewWidth, y: y))
                }
            }
            .stroke(Color.gray.opacity(0.2), lineWidth: 1)
            
            // Target Pitch Curve (Blue)
            drawCurve(points: targetHistory, color: .blue.opacity(0.5))
            
            // Live Pitch Curve (Green/Red)
            drawCurve(points: liveHistory, color: .green)
            
            // Current Time Indicator
            Rectangle()
                .fill(Color.red)
                .frame(width: 2)
                .offset(x: viewWidth / 2 - viewWidth) // Center line
        }
        .frame(width: viewWidth, height: viewHeight)
        .background(Color.black.opacity(0.05))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
    
    private func drawCurve(points: [PitchPoint], color: Color) -> some View {
        Path { path in
            let filteredPoints = points.filter { $0.time > currentTime - timeWindow / 2 && $0.time < currentTime + timeWindow / 2 }
            
            for (index, point) in filteredPoints.enumerated() {
                let x = CGFloat((point.time - (currentTime - timeWindow / 2)) / timeWindow) * viewWidth
                let y = viewHeight - CGFloat(min(point.frequency / 5, Float(viewHeight))) // Simple scaling
                
                if index == 0 {
                    path.move(to: CGPoint(x: x, y: y))
                } else {
                    path.addLine(to: CGPoint(x: x, y: y))
                }
            }
        }
        .stroke(color, style: StrokeStyle(lineWidth: 3, lineCap: .round, lineJoin: .round))
    }
}

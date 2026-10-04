// OCR via macOS Vision: ocr IMG [IMG...] -> JSON [{image, lines:[{text, conf, x, y, w, h}]}] (normalized, origin top-left)
import Foundation
import Vision
import AppKit

var out: [[String: Any]] = []
for path in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { continue }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = false
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    try? handler.perform([req])
    var lines: [[String: Any]] = []
    for obs in (req.results ?? []) {
        guard let cand = obs.topCandidates(1).first else { continue }
        let b = obs.boundingBox
        lines.append(["text": cand.string, "conf": cand.confidence, "x": b.minX, "y": 1.0 - b.maxY, "w": b.width, "h": b.height])
    }
    out.append(["image": path, "lines": lines])
}
let data = try JSONSerialization.data(withJSONObject: out, options: [])
print(String(data: data, encoding: .utf8)!)

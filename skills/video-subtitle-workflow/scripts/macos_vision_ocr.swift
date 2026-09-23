import AppKit
import Foundation
import Vision

struct OCRBox: Codable {
    let text: String
    let confidence: Float
    let x: Int
    let y: Int
    let width: Int
    let height: Int
}

struct OCRFrame: Codable {
    let frame: Int
    let path: String
    let width: Int
    let height: Int
    let boxes: [OCRBox]
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write((message + "\n").data(using: .utf8)!)
    exit(1)
}

guard CommandLine.arguments.count == 3 else {
    fail("用法: swift macos_vision_ocr.swift <帧目录> <输出jsonl>")
}

let frameDirectory = URL(fileURLWithPath: CommandLine.arguments[1])
let outputURL = URL(fileURLWithPath: CommandLine.arguments[2])
let fileManager = FileManager.default
let frameURLs = try fileManager.contentsOfDirectory(
    at: frameDirectory,
    includingPropertiesForKeys: nil
).filter { $0.pathExtension.lowercased() == "png" }.sorted { $0.lastPathComponent < $1.lastPathComponent }

fileManager.createFile(atPath: outputURL.path, contents: nil)
guard let output = try? FileHandle(forWritingTo: outputURL) else {
    fail("无法写入: \(outputURL.path)")
}
defer { try? output.close() }

let encoder = JSONEncoder()
for (offset, frameURL) in frameURLs.enumerated() {
    guard let image = NSImage(contentsOf: frameURL),
          let tiff = image.tiffRepresentation,
          let bitmap = NSBitmapImageRep(data: tiff),
          let cgImage = bitmap.cgImage else { continue }

    let imageWidth = cgImage.width
    let imageHeight = cgImage.height
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["zh-Hans", "zh-Hant"]
    request.usesLanguageCorrection = true

    let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    try handler.perform([request])
    let boxes: [OCRBox] = (request.results ?? []).compactMap { observation in
        guard let candidate = observation.topCandidates(1).first else { return nil }
        let box = observation.boundingBox
        return OCRBox(
            text: candidate.string,
            confidence: candidate.confidence,
            x: Int((box.minX * CGFloat(imageWidth)).rounded()),
            y: Int(((1 - box.maxY) * CGFloat(imageHeight)).rounded()),
            width: Int((box.width * CGFloat(imageWidth)).rounded()),
            height: Int((box.height * CGFloat(imageHeight)).rounded())
        )
    }

    let record = OCRFrame(
        frame: offset + 1,
        path: frameURL.path,
        width: imageWidth,
        height: imageHeight,
        boxes: boxes
    )
    let data = try encoder.encode(record)
    output.write(data)
    output.write(Data([0x0A]))
}

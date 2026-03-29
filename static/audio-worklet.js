class PcmCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.bufferSize = 8192;
    this.pending = new Float32Array(this.bufferSize);
    this.pendingLength = 0;
  }

  process(inputs) {
    const input = inputs[0];
    if (input && input[0] && input[0].length) {
      const samples = input[0];
      let offset = 0;

      while (offset < samples.length) {
        const remaining = this.bufferSize - this.pendingLength;
        const copyLength = Math.min(remaining, samples.length - offset);

        this.pending.set(samples.subarray(offset, offset + copyLength), this.pendingLength);
        this.pendingLength += copyLength;
        offset += copyLength;

        if (this.pendingLength === this.bufferSize) {
          this.port.postMessage(this.pending.slice(0));
          this.pendingLength = 0;
        }
      }
    }
    return true;
  }
}

registerProcessor("pcm-capture-processor", PcmCaptureProcessor);

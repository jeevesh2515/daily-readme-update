# Hosted at https://github.com/jeevesh2515/homebrew-tap
# Formula for readme-guardian
class ReadmeGuardian < Formula
  desc "README freshness guarantee for vibe coders — auto-syncs README.md with live data"
  homepage "https://github.com/jeevesh2515/readme-guardian"
  url "https://github.com/jeevesh2515/readme-guardian/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000" # Set on release
  license "MIT"

  depends_on "python@3.12"
  depends_on "pipx"

  def install
    system "pipx", "install", "--python", Formula["python@3.12"].opt_bin/"python3.12",
           "readme-guardian==#{version}", "--verbose"
    bin.install_symlink Dir["#{Dir.home}/.local/bin/readme-guardian"]
  end

  test do
    assert_match "readme-guardian v#{version}", shell_output("#{bin}/readme-guardian --version")
  end
end

MIME_MAP = {
    "": "text/plain",
    ".aar": "application/java-archive",
    ".apk": "application/vnd.android.package-archive",
    ".asc": "text/plain",
    ".beet": "text/plain",
    ".bundle": "application/octet-stream",
    ".bz2": "application/octet-stream",
    ".checksums": "text/plain",
    ".dmg": "application/x-iso9660-image",
    ".jar": "application/java-archive",
    ".json": "application/json",
    ".mar": "application/octet-stream",
    ".md5": "text/plain",
    ".module": "application/json",
    ".msi": "application/x-msi",
    # Per https://docs.microsoft.com/en-us/windows/msix/app-installer/web-install-iis
    ".msix": "application/msix",
    ".pkg": "application/x-newton-compatible-pkg",
    ".pom": "application/xml",
    ".rcc": "application/octet-stream",
    ".sha1": "text/plain",
    ".sha256": "text/plain",
    ".sha512": "text/plain",
    ".sig": "application/octet-stream",
    ".snap": "application/octet-stream",
    ".xpi": "application/x-xpinstall",
}

STAGE_PLATFORM_MAP = {
    "linux": "linux-i686",
    "linux-devedition": "linux-i686",
    "linux64": "linux-x86_64",
    "linux64-asan-reporter": "linux-x86_64-asan-reporter",
    "linux64-devedition": "linux-x86_64",
    "linux64-pinebuild": "linux-x86_64",
    "macosx64": "mac",
    "macosx64-asan-reporter": "mac-asan-reporter",
    "macosx64-devedition": "mac",
    "macosx64-pinebuild": "mac",
    "win32-devedition": "win32",
    "win64-devedition": "win64",
    "win64-pinebuild": "win64",
    "win64-aarch64-devedition": "win64-aarch64",
    "win64-aarch64-pinebuild": "win64-aarch64",
}

NORMALIZED_BALROG_PLATFORMS = {
    "linux-devedition": "linux",
    "linux64-devedition": "linux64",
    "linux64-pinebuild": "linux64",
    "macosx64-devedition": "macosx64",
    "macosx64-pinebuild": "macosx64",
    "win32-devedition": "win32",
    "win64-devedition": "win64",
    "win64-pinebuild": "win64",
    "win64-aarch64-devedition": "win64-aarch64",
    "win64-aarch64-pinebuild": "win64-aarch64",
}

NORMALIZED_FILENAME_PLATFORMS = NORMALIZED_BALROG_PLATFORMS.copy()
NORMALIZED_FILENAME_PLATFORMS.update(
    {
        "android": "android-arm",
        "android-api-15": "android-arm",
        "android-api-15-old-id": "android-arm",
        "android-api-16": "android-arm",
        "android-api-16-old-id": "android-arm",
        "android-x86": "android-i386",
        "android-x86-old-id": "android-i386",
        "android-aarch64": "android-aarch64",
    }
)

HASH_BLOCK_SIZE = 1024 * 1024

RELEASE_BRANCHES = ("mozilla-central", "mozilla-beta", "mozilla-release", "mozilla-esr52" "comm-central", "comm-beta", "comm-esr60")

# actions that imply actual releases, hence the need of `build_number` and
# `version`
PROMOTION_ACTIONS = ("push-to-candidates",)

RELEASE_ACTIONS = ("push-to-releases",)

DIRECT_RELEASE_ACTIONS = ("direct-push-to-bucket",)

PARTNER_REPACK_ACTIONS = ("push-to-partner",)

MAVEN_ACTIONS = ("push-to-maven",)

ARTIFACT_REGISTRY_ACTIONS = ("import-artifacts",)

# XXX this is a fairly clunky way of specifying which files to copy from
# candidates to releases -- let's find a nicer way of doing this.
# XXX if we keep this, let's make it configurable? overridable in config?
# Faster to update a config file in puppet than to ship a new beetmover release
# and update in puppet
RELEASE_EXCLUDE = (
    r"^.*tests.*$",
    r"^.*crashreporter.*$",
    r"^(?!.*jsshell-).*\.zip(\.asc)?$",
    r"^.*\.log$",
    r"^.*\.txt$",
    r"^.*/partner-repacks.*$",
    r"^.*.checksums(\.asc)?$",
    r"^.*/logs/.*$",
    r"^.*json$",
    r"^.*/host.*$",
    r"^.*/mar-tools/.*$",
    r"^.*robocop.apk$",
    r"^.*contrib.*",
    r"^.*/beetmover-checksums/.*$",
)

CACHE_CONTROL_MAXAGE = 3600 * 4

PRODUCT_TO_PATH = {
    "mobile": "pub/mobile/",
    "fennec": "pub/mobile/",
    "devedition": "pub/devedition/",
    "pinebuild": "pub/pinebuild/",
    "firefox": "pub/firefox/",
    "thunderbird": "pub/thunderbird/",
    "vpn": "pub/vpn/",
}

PARTNER_REPACK_PUBLIC_PREFIX_TMPL = "pub/firefox/candidates/{version}-candidates/build{build_number}/"
PARTNER_REPACK_PRIVATE_REGEXES = (
    r"^(?P<partner>[^\/%]+)\/{version}-{build_number}\/(?P<subpartner>[^\/%]+)\/(mac|win32|win64(|-aarch64)|linux-i686|linux-x86_64)\/(?P<locale>[^\/%]+)$",
)
PARTNER_REPACK_PUBLIC_REGEXES = (
    r"^(beetmover-checksums\/)?(mac|win32|win64(|-aarch64))-EME-free\/[^\/.]+$",
    r"^partner-repacks\/(?P<partner>[^\/%]+)\/(?P<subpartner>[^\/%]+)\/v\d+\/(mac|win32|win64(|-aarch64)|linux-i686|linux-x86_64)\/(?P<locale>[^\/%]+)$",
)

CHECKSUMS_CUSTOM_FILE_NAMING = {"beetmover-source": "-source", "release-beetmover-signed-langpacks": "-langpack"}

BUILDHUB_ARTIFACT = "buildhub.json"

# the installer artifact for each platform
INSTALLER_ARTIFACTS = ("target.tar.bz2", "target.installer.exe", "target.dmg", "target.apk")

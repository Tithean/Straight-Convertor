import subprocess
from pathlib import Path

from app.core.errors import ConversionError


class OfficeToPdfConverter:
    def convert(
        self, source: Path, output: Path, *, office_path: str | None, max_pages: int
    ) -> None:
        if not office_path:
            raise ConversionError(
                "Office conversion is unavailable. Please try again later.",
                503,
                "engine_unavailable",
            )

        profile = source.parent / "office-profile"
        profile.mkdir()
        # An isolated profile prevents simultaneous requests from sharing an Office session.
        # Disable macros and link updates for untrusted uploads.
        (profile / "user").mkdir()
        (profile / "user" / "registrymodifications.xcu").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<oor:items xmlns:oor="http://openoffice.org/2001/registry">'
            '<item oor:path="/org.openoffice.Office.Common/Security/Scripting">'
            '<prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop></item>'
            '<item oor:path="/org.openoffice.Office.Common/Load">'
            '<prop oor:name="UpdateLink" oor:op="fuse"><value>0</value></prop></item>'
            "</oor:items>",
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                office_path,
                f"-env:UserInstallation={profile.as_uri()}",
                "--headless",
                "--nologo",
                "--nodefault",
                "--norestore",
                "--convert-to",
                "pdf",
                "--outdir",
                str(output.parent),
                str(source),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        generated = output.parent / f"{source.stem}.pdf"
        if (
            result.returncode != 0
            or not generated.is_file()
            or generated.stat().st_size == 0
        ):
            raise ConversionError(
                "This document could not be converted. Check that it opens correctly and is not password protected."
            )
        if generated != output:
            generated.rename(output)

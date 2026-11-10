"""image_export_mode=placeholder must also leave the image data out of JSON."""

import json
from pathlib import Path, PurePath

import pytest
from PIL import Image

from docling.datamodel.base_models import ConversionStatus
from docling_core.types.doc import DoclingDocument, ImageRef, ImageRefMode, Size

from docling_jobkit.convert.export import _materialize_document_exports
from docling_jobkit.convert.results import _export_document_as_content
from docling_jobkit.datamodel.exportable_document import ExportableDocument


def _document_with_images() -> ExportableDocument:
    image = ImageRef.from_pil(Image.new("RGB", (32, 32), "red"), dpi=72)
    document = DoclingDocument(name="with-images")
    document.add_page(page_no=1, size=Size(width=32, height=32), image=image)
    document.add_picture(image=image)
    return ExportableDocument(
        file=PurePath("with-images.pdf"),
        status=ConversionStatus.SUCCESS,
        document=document,
    )


def _content(image_mode: ImageRefMode) -> DoclingDocument:
    response = _export_document_as_content(
        _document_with_images(),
        export_json=True,
        export_html=False,
        export_md=False,
        export_txt=False,
        export_doctags=False,
        export_doclang=False,
        image_mode=image_mode,
        md_page_break_placeholder="",
        md_compact_tables=False,
    )
    assert response.json_content is not None
    return response.json_content


def test_placeholder_json_content_has_no_image_data():
    doc = _content(ImageRefMode.PLACEHOLDER)

    assert doc.pictures[0].image is None
    assert doc.pages[1].image is None
    assert "data:image" not in doc.model_dump_json()


def test_embedded_json_content_keeps_image_data():
    doc = _content(ImageRefMode.EMBEDDED)

    assert doc.pictures[0].image is not None
    assert str(doc.pictures[0].image.uri).startswith("data:image")


def test_placeholder_leaves_the_converted_document_unchanged():
    exportable = _document_with_images()
    _export_document_as_content(
        exportable,
        export_json=True,
        export_html=False,
        export_md=False,
        export_txt=False,
        export_doctags=False,
        export_doclang=False,
        image_mode=ImageRefMode.PLACEHOLDER,
        md_page_break_placeholder="",
        md_compact_tables=False,
    )

    assert exportable.document is not None
    assert exportable.document.pictures[0].image is not None


@pytest.mark.parametrize(
    ("image_mode", "has_image_data"),
    [(ImageRefMode.PLACEHOLDER, False), (ImageRefMode.EMBEDDED, True)],
)
def test_json_artifact_follows_image_export_mode(
    tmp_path: Path, image_mode: ImageRefMode, has_image_data: bool
):
    _materialize_document_exports(
        _document_with_images(),
        tmp_path,
        export_json=True,
        export_html=False,
        export_md=False,
        export_txt=False,
        export_doctags=False,
        export_doclang=False,
        export_dclx=False,
        image_export_mode=image_mode,
        md_page_break_placeholder="",
        md_compact_tables=False,
        bundle_resources=False,
    )

    written = (tmp_path / "with-images.json").read_text(encoding="utf-8")
    assert ("data:image" in written) == has_image_data
    assert json.loads(written)["pictures"]

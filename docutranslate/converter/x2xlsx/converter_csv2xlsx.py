# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import asyncio
import csv
from dataclasses import dataclass
from io import BytesIO, StringIO
from typing import Hashable

import charset_normalizer
import openpyxl

from docutranslate.converter.x2xlsx.base import X2XlsxConverter, X2XlsxConverterConfig
from docutranslate.ir.document import Document


# 配置一个基本的日志记录器（如果您的项目尚未配置）
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
@dataclass(kw_only=True)
class ConverterCsv2XlsxConfig(X2XlsxConverterConfig):

    def gethash(self) -> Hashable:
        return "1"


class ConverterCsv2Xlsx(X2XlsxConverter):
    """
    一个经过改进的、健壮的 CSV 到 XLSX 转换器.

    特性:
    - 内存高效：使用流式写入模式处理大型файл.
    - 自动编码检测：避免乱码问题.
    - 自动 CSV 格式识别：支持不同的分隔符.
    - 完善的помилка处理和日志记录.
    """

    def __init__(self, config: ConverterCsv2XlsxConfig):
        super().__init__(config=config)

    def convert(self, document: Document) -> Document:
        """
        将 CSV Document 对象同步转换为 XLSX Document 对象.
        """
        self.logger.info(f"Починаю конвертацію файлу {document.name} (розмір: {len(document.content)} bytes)")

        try:
            # --- 1. 自动检测файл编码 ---
            # 为提高性能，只取файл头部一部分进行检测
            detection_result = charset_normalizer.detect(document.content[:4096])
            encoding = detection_result['encoding'] or 'utf-8'  # 提供一个默认值
            confidence = detection_result['confidence']
            self.logger.info(f"Виявлено кодування файлу: {encoding} (впевненість: {confidence:.2%})")

            # --- 2. 解码并创建文本流 ---
            try:
                decoded_content = document.content.decode(encoding)
            except UnicodeDecodeError:
                self.logger.warning(f"Використання виявленого кодування '{encoding}' не вдалось декодувати, пробую 'utf-8'.")
                decoded_content = document.content.decode('utf-8', errors='replace')

            csv_text_stream = StringIO(decoded_content)

            # --- 3. 自动识别CSV方言（如分隔符） ---
            try:
                # Sniffer需要一些数据来嗅探，如果файл太小可能失败
                dialect = csv.Sniffer().sniff(csv_text_stream.read(2048))
                csv_text_stream.seek(0)  # 将流指针重置回файл开头
                self.logger.info(f"Виявлено роздільник CSV: '{dialect.delimiter}'")
            except csv.Error:
                self.logger.warning("Не вдалось автоматично визначити діалект CSV, використовую кому за замовчуванням.")
                dialect = 'excel'  # 使用默认方言
                csv_text_stream.seek(0)

            csv_reader = csv.reader(csv_text_stream, dialect)

            # --- 4. 使用内存优化的`write_only`模式创建XLSX ---
            wb = openpyxl.Workbook(write_only=True)
            ws = wb.create_sheet()

            # --- 5. 逐行读取CSV并写入XLSX ---
            row_count = 0
            for row_data in csv_reader:
                ws.append(row_data)  # append() 是 write_only 模式下的高效写入方法
                row_count += 1

            self.logger.info(f"Оброблено {row_count} рядків даних.")

            # --- 6. 将生成的XLSX保存到内存中的字节流 ---
            output_buffer = BytesIO()
            wb.save(output_buffer)
            output_buffer.seek(0)  # 将指针移到开头，以便getvalue()读取完整内容

            self.logger.info(f"файл {document.name} успішно конвертовано у XLSX.")

            return Document.from_bytes(
                content=output_buffer.getvalue(),
                suffix=".xlsx",
                stem=document.stem
            )

        except Exception as e:
            self.logger.error(f"Конвертація файлу {document.name} критична помилка: {e}", exc_info=True)
            # 根据您的业务逻辑，这里可以抛出异常或返回一个表示失败的特定对象
            raise

    async def convert_async(self, document: Document) -> Document:
        """
        异步执行转换操作.
        由于核心转换逻辑是CPU密集型和阻塞IO，使用 to_thread 是正确的选择，
        它可以防止阻塞asyncio事件循环.
        """
        self.logger.info(f"Для файлу {document.name} створено новий потік для конвертації.")
        # 我们已经优化了 `convert` 方法，所以 `to_thread` 的方式非常适合
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.convert, document)

    def support_format(self) -> list[str]:
        """
        声明此转换器支持的源файл格式.
        """
        return [".csv"]

# import wmill
from typing import Dict, List, Set, Union, Any
import requests
import bisect
import pytz
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

TBI_DOCS_URL = os.getenv("TBI_DOCS_URL")
if not TBI_DOCS_URL:
    raise ValueError("TBI_DOCS_URL environment variable is required")

SESSION_DATA_TBI = os.getenv("SESSION_DATA_TBI")
if not SESSION_DATA_TBI:
    raise ValueError("SESSION_DATA_TBI environment variable is required")


class TBICalculator:
    """
    TBI Calculator - Tính toán các chỉ số hành vi giao dịch

    Dựa trên tên, ngày sinh và thông tin cá nhân để tính toán
    các chỉ số TBI (Trading Behavior Intelligence)
    """

    # Mapping alphabet to numbers (similar to numerology system)
    ALPHABET = {
        # Basic alphabet
        "A": 1,
        "B": 2,
        "C": 3,
        "D": 4,
        "E": 5,
        "F": 6,
        "G": 7,
        "H": 8,
        "I": 9,
        "J": 1,
        "K": 2,
        "L": 3,
        "M": 4,
        "N": 5,
        "O": 6,
        "P": 7,
        "Q": 8,
        "R": 9,
        "S": 1,
        "T": 2,
        "U": 3,
        "V": 4,
        "W": 5,
        "X": 6,
        "Y": 7,
        "Z": 8,
        # Vowels with diacritics
        "Ă": 1,
        "Â": 1,
        "Ê": 5,
        "Ô": 6,
        "Ơ": 6,
        # Consonants with diacritics
        "Đ": 4,
        # Vowels with tone
        "Á": 1,
        "À": 1,
        "Ả": 1,
        "Ã": 1,
        "Ạ": 1,
        "Ắ": 1,
        "Ằ": 1,
        "Ẳ": 1,
        "Ẵ": 1,
        "Ặ": 1,
        "Ấ": 1,
        "Ầ": 1,
        "Ẩ": 1,
        "Ẫ": 1,
        "Ậ": 1,
        "É": 5,
        "È": 5,
        "Ẻ": 5,
        "Ẽ": 5,
        "Ẹ": 5,
        "Ế": 5,
        "Ề": 5,
        "Ể": 5,
        "Ễ": 5,
        "Ệ": 5,
        "Í": 9,
        "Ì": 9,
        "Ỉ": 9,
        "Ĩ": 9,
        "Ị": 9,
        "Ó": 6,
        "Ò": 6,
        "Ỏ": 6,
        "Õ": 6,
        "Ọ": 6,
        "Ố": 6,
        "Ồ": 6,
        "Ổ": 6,
        "Ỗ": 6,
        "Ộ": 6,
        "Ớ": 6,
        "Ờ": 6,
        "Ở": 6,
        "Ỡ": 6,
        "Ợ": 6,
        # U and variants
        "Ú": 3,
        "Ù": 3,
        "Ủ": 3,
        "Ũ": 3,
        "Ụ": 3,
        "Ư": 3,
        "Ứ": 3,
        "Ừ": 3,
        "Ử": 3,
        "Ữ": 3,
        "Ự": 3,
        # Y variants
        "Ý": 7,
        "Ỳ": 7,
        "Ỷ": 7,
        "Ỹ": 7,
        "Ỵ": 7,
    }

    # Master numbers
    MASTER_NUMBERS = {11, 22, 33}

    # Karmic debt numbers
    KARMIC_NUMBERS = {13, 14, 16, 19}

    def __init__(self, dob: str, name: str, current_date: str = None):
        """
        Initialize TBI Calculator with name, birthday and current date similar to numerology calculation

        Args:
            dob: Birthday (dd/mm/yyyy)
            name: Full name
            current_date: Current date (dd/mm/yyyy), default is today similar to numerology calculation
        """
        self.dob = dob
        self.name = name.upper().strip()

        # Handle current_date parameter
        if current_date is None or current_date == "" or current_date.strip() == "":
            vntz = pytz.timezone("Asia/Ho_Chi_Minh")
            self.current_datetime = datetime.now(vntz)
        else:
            self.current_datetime = self._parse_date(current_date, "current")

        # Parse dates
        self.dob_date = self._parse_date(dob, "birthday")

        # Convert name to numbers
        self.name_numbers = self._name_to_numbers()

        # Parse date components
        self.dob_day = self.dob_date.day
        self.dob_month = self.dob_date.month
        self.dob_year = self.dob_date.year

        # Calculate reduced date components
        self.day_r = self.reduce_number_with_masters(self.dob_day)
        self.month_r = self.reduce_number_with_masters(self.dob_month)
        self.year_r = self.reduce_number_with_masters(self.dob_year)

        # Calculate date no master
        self.day_r_no_master = self.reduce_number_no_master(self.dob_day)
        self.month_r_no_master = self.reduce_number_no_master(self.dob_month)
        self.year_r_no_master = self.reduce_number_no_master(self.dob_year)

    def _parse_date(self, date_str: str, date_type: str) -> datetime:
        """Parse date string to datetime object."""
        try:
            return datetime.strptime(date_str, "%d/%m/%Y")
        except ValueError:
            if date_type in ["current date", "current"]:
                # Use current time if current date is invalid
                vn_timezone = pytz.timezone("Asia/Ho_Chi_Minh")
                return datetime.now(vn_timezone)
            else:
                raise ValueError(
                    f"Invalid {date_type} format. Use 'dd/mm/yyyy' format."
                )

    def _name_to_numbers(self) -> List[int]:
        """Convert name to list of numbers using ALPHABET mapping."""
        # Remove spaces and convert to uppercase
        clean_name = "".join(self.name.upper().split())
        return [
            self.ALPHABET.get(char, 0) for char in clean_name if char in self.ALPHABET
        ]

    def reduce_number(self, n: int) -> int:
        """
        Reduce number to single digit or master number (11, 22).

        Args:
            n: Number to reduce

        Returns:
            Reduced number (1-9, 11, or 22)
        """
        while n > 9 and n not in {11, 22}:
            n = sum(int(digit) for digit in str(n))
        return n

    def reduce_number_no_master(self, n: int) -> int:
        """
        Reduce number to single digit. (1-9)
        """
        while n > 9:
            n = sum(int(digit) for digit in str(n))
        return n

    def reduce_number_with_masters(self, n: int, masters: Set[int] = None) -> int:
        """
        Reduce number keeping master numbers (11, 22, 33).

        Args:
            n: Number to reduce
            masters: Set of master numbers to preserve (default: {11, 22, 33})

        Returns:
            Reduced number (1-9, 11, 22, or 33)
        """
        if masters is None:
            masters = self.MASTER_NUMBERS

        while n > 9 and n not in masters:
            n = sum(int(digit) for digit in str(n))
        return n

    def reduce_to_single_digit(self, n: int) -> int:
        """
        Always reduce to single digit (1-9).

        Args:
            n: Number to reduce

        Returns:
            Single digit (1-9)
        """
        while n > 9:
            n = sum(int(digit) for digit in str(n))
        return n

    def _is_vowel(self, char: str, current_word: str = None) -> bool:
        """
        Check if character is a vowel for soul number calculation.

        Rules:
        1. A, E, I, O, U, Y are vowels
        2. Variants with diacritics (Â, Ă, Ê, Ô, Ơ, etc.) are vowels
        3. Y is only a vowel when:
           - It's the only vowel in the word, OR
           - It stands alone
        4. All other cases with Y are consonants
        """
        char_upper = char.upper()

        # Basic vowels: A, E, I, O, U
        basic_vowels = {
            "A",
            "E",
            "I",
            "O",
            "U",
            # A variants with diacritics
            "Á",
            "À",
            "Ả",
            "Ã",
            "Ạ",
            "Ắ",
            "Ằ",
            "Ẳ",
            "Ẵ",
            "Ặ",
            "Ấ",
            "Ầ",
            "Ẩ",
            "Ẫ",
            "Ậ",
            "Ă",
            "Â",
            # E variants with diacritics
            "É",
            "È",
            "Ẻ",
            "Ẽ",
            "Ẹ",
            "Ế",
            "Ề",
            "Ể",
            "Ễ",
            "Ệ",
            "Ê",
            # I variants with diacritics
            "Í",
            "Ì",
            "Ỉ",
            "Ĩ",
            "Ị",
            # O variants with diacritics
            "Ó",
            "Ò",
            "Ỏ",
            "Õ",
            "Ọ",
            "Ố",
            "Ồ",
            "Ổ",
            "Ỗ",
            "Ộ",
            "Ớ",
            "Ờ",
            "Ở",
            "Ỡ",
            "Ợ",
            "Ô",
            "Ơ",
            # U variants with diacritics
            "Ú",
            "Ù",
            "Ủ",
            "Ũ",
            "Ụ",
            "Ứ",
            "Ừ",
            "Ử",
            "Ữ",
            "Ự",
            "Ư",
        }

        # Check if it's a basic vowel
        if char_upper in basic_vowels:
            return True

        # Special handling for Y
        if char_upper == "Y" or char_upper in {"Ý", "Ỳ", "Ỷ", "Ỹ", "Ỵ"}:
            if current_word:
                return self._is_y_vowel_in_word(char, current_word)
            else:
                # Fallback: find the word containing this Y character
                word = self._find_word_with_char_at_position(char)
                return self._is_y_vowel_in_word(char, word)

        return False

    def _is_y_vowel_in_word(self, char: str, word: str) -> bool:
        """
        Check if Y is a vowel in the given word.

        Y is a vowel when:
        - It's the only vowel in the word, OR
        - It stands alone
        """
        if not word:
            return False

        # Count other vowels in the word (excluding this Y)
        other_vowels_count = 0
        for c in word:
            if c.upper() != "Y":
                c_upper = c.upper()
                # Check if it's a vowel (A, E, I, O, U and their variants)
                if c_upper in {
                    "A",
                    "E",
                    "I",
                    "O",
                    "U",
                    "Ă",
                    "Â",
                    "Ê",
                    "Ô",
                    "Ơ",
                    "Ư",
                } or c_upper in {
                    "Á",
                    "À",
                    "Ả",
                    "Ã",
                    "Ạ",
                    "Ắ",
                    "Ằ",
                    "Ẳ",
                    "Ẵ",
                    "Ặ",
                    "Ấ",
                    "Ầ",
                    "Ẩ",
                    "Ẫ",
                    "Ậ",
                    "É",
                    "È",
                    "Ẻ",
                    "Ẽ",
                    "Ẹ",
                    "Ế",
                    "Ề",
                    "Ể",
                    "Ễ",
                    "Ệ",
                    "Í",
                    "Ì",
                    "Ỉ",
                    "Ĩ",
                    "Ị",
                    "Ó",
                    "Ò",
                    "Ỏ",
                    "Õ",
                    "Ọ",
                    "Ố",
                    "Ồ",
                    "Ổ",
                    "Ỗ",
                    "Ộ",
                    "Ớ",
                    "Ờ",
                    "Ở",
                    "Ỡ",
                    "Ợ",
                    "Ú",
                    "Ù",
                    "Ủ",
                    "Ũ",
                    "Ụ",
                    "Ứ",
                    "Ừ",
                    "Ử",
                    "Ữ",
                    "Ự",
                }:
                    other_vowels_count += 1

        # Y is vowel if it's the only vowel in the word
        return other_vowels_count == 0

    def _find_word_with_char_at_position(self, char: str) -> str:
        """
        Find the word containing the given character at its specific position.
        """
        name_parts = self._split_name_parts()

        # Find the position of this character in the original name
        char_pos = self.name.find(char)
        if char_pos == -1:
            return ""

        # Find which word contains this character at this position
        current_pos = 0
        for part in name_parts:
            part_start = current_pos
            part_end = current_pos + len(part)

            if part_start <= char_pos < part_end:
                return part

            current_pos = part_end + 1  # +1 for space

        return ""

    def _is_consonant(self, char: str, current_word: str = None) -> bool:
        """Check if character is a consonant."""
        return not self._is_vowel(char, current_word)

    def _split_name_parts(self) -> List[str]:
        """Split name into individual parts (words)."""
        return [part.strip() for part in self.name.split() if part.strip()]

    def calculate_ppa(self) -> int:
        """Calculate Path Potential Alignment

        Formula: reduce_number_with_masters(day + month + year) (keep master numbers)
        """
        return self.reduce_number_with_masters(self.day_r + self.month_r + self.year_r)

    def calculate_spi(self) -> int:
        """
        Calculate Skill Potential Index.

        Formula: reduce_number_with_masters(sum(nameNumbers)) (keep master numbers)
        """
        return self.reduce_number_with_masters(sum(self.name_numbers))

    def calculate_cmi(self) -> int:
        """
        Calculate Crisis Management Index.

        Formula: reduce_to_single_digit(sum(first_letters)) (always 1 digit)
        Get the first letter of each word in the full name, add all of them
        """
        name_parts = self._split_name_parts()
        if len(name_parts) < 1:  # Only need at least 1 word
            return 0

        first_letters_sum = 0
        for part in name_parts:
            if part:
                first_letter = part[0].upper()
                first_letters_sum += self.ALPHABET.get(first_letter, 0)

        return self.reduce_to_single_digit(first_letters_sum)

    def calculate_edi(self) -> int:
        """
        Calculate Emotional Drive Index.

        Formula: reduce_number_with_masters(sum(reduce_number_with_masters(sum(vowels(part))) for part in parts))
        """
        name_parts = self._split_name_parts()
        soul_sum = 0

        for part in name_parts:
            part_vowels_sum = sum(
                self.ALPHABET.get(char.upper(), 0)
                for char in part
                if self._is_vowel(char, part)
            )
            soul_sum += self.reduce_number_with_masters(part_vowels_sum)

        return self.reduce_number_with_masters(soul_sum)

    def calculate_mpi(self) -> int:
        """
        Calculate Market Persona Index.

        Formula: reduce_number_with_masters(sum(reduce_number_with_masters(sum(consonants(part))) for part in parts))
        """
        name_parts = self._split_name_parts()
        personality_sum = 0

        for part in name_parts:
            part_consonants_sum = sum(
                self.ALPHABET.get(char.upper(), 0)
                for char in part
                if self._is_consonant(char)
            )
            personality_sum += self.reduce_number_with_masters(part_consonants_sum)

        return self.reduce_number_with_masters(personality_sum)

    def calculate_nei(self) -> int:
        """
        Calculate Natural Edge Index.

        Formula: reduce_number(day) (keep master number 11/22)
        """
        return self.reduce_number_with_masters(self.dob_day)

    def calculate_ssi(self) -> int:
        """
        Calculate Subconscious Stability Index.

        Formula: 9 - count(missing_aspects)
        (missing_aspects are numbers 1..9 not in nameNumbers)
        """
        missing_aspects = self.get_wmi()
        return 9 - len(missing_aspects)

    def calculate_ri(self) -> int:
        """
        Calculate Resilience Index.

        Formula: reduce_number(life_path + life_purpose) (keep master number 11/22)
        """
        life_path = self.calculate_ppa()
        life_purpose = self.calculate_spi()
        return self.reduce_number_with_masters(life_path + life_purpose)

    def get_wmi(self) -> Set[int]:
        """
        Get Weakness Map Index.

        Returns:
            Set of numbers 1-9 not appearing in name_numbers
        """
        name_digits = set()
        for num in self.name_numbers:
            for digit in str(num):
                if digit.isdigit():
                    name_digits.add(int(digit))

        return sorted(set(range(1, 10)) - name_digits)

    def check_bli(self) -> str:
        """
        Check for Behavioral Liability Index.

        Formula:
        - karmic = {13, 14, 16, 19}
        - dobSum = sum(all digits in day, month, year)
        - If dobSum ∈ karmic or sum(nameNumbers) ∈ karmic ⇒ "Has Karmic Debt"
        """
        # Sum of all digits in date of birth
        dob_sum = sum(
            int(digit) for digit in f"{self.dob_day}{self.dob_month}{self.dob_year}"
        )

        # Sum of name numbers
        name_sum = sum(self.name_numbers)

        if dob_sum in self.KARMIC_NUMBERS or name_sum in self.KARMIC_NUMBERS:
            return "Có Karmic Debt"
        return "Không có Karmic Debt"

    def calculate_sai(self) -> List[int]:
        """
        Calculate Strength Amplifier Index.

        Formula: Count frequency of numbers in nameNumbers, get the most frequent numbers
        """
        from collections import Counter

        digit_counts = Counter()
        for num in self.name_numbers:
            for digit in str(num):
                if digit.isdigit():
                    digit_counts[int(digit)] += 1

        if not digit_counts:
            return []

        max_freq = max(digit_counts.values())
        return sorted([num for num, freq in digit_counts.items() if freq == max_freq])

    def get_societal_adaptability_index(self) -> str:
        """
        Get societal adaptability index based on birth year.

        Formula:
        - 1981–1996: "Gen Y (Millennials) - Cân bằng công việc-cuộc sống, công nghệ"
        - 1997–2012: "Gen Z - Công nghệ số, đa dạng, thay đổi nhanh"
        - Khác: "Khác"
        """
        if 1981 <= self.dob_year <= 1996:
            return "Gen Y (Millennials) - Cân bằng công việc-cuộc sống, công nghệ"
        elif 1997 <= self.dob_year <= 2012:
            return "Gen Z - Công nghệ số, đa dạng, thay đổi nhanh"
        else:
            return "Khác"

    def calculate_ppai(self) -> int:
        """
        Calculate Path–Potential Alignment Index.

        Formula: reduceNumber(abs(soul - personality)) (Keep master number 11/22)
        """
        lifepath = self.calculate_ppa()
        life_purpose = self.calculate_spi()
        return self.reduce_number(abs(lifepath - life_purpose))

    def calculate_ioci(self) -> int:
        """
        Calculate Inner–Outer Coherence Index.

        Formula: reduceToSingleDigit(abs(soul - personality)) (1 digit)
        """
        soul = self.calculate_edi()
        if soul in [11, 22, 33]:
            soul = sum(int(digit) for digit in str(soul))
        personality = self.calculate_mpi()
        return self.reduce_to_single_digit(abs(soul - personality))

    def calculate_tci_phase(self) -> Dict[str, int]:
        """
        Calculate Trading Cycle Index Phase.

        Formula (keep master number 11/22 at each reduceNumber step):
        - dayM = reduceNumber(day); monthM = reduceNumber(month); yearM = reduceNumber(year)
        - tci_1 = reduceNumber(monthM + dayM)     // Month + Day
        - tci_2 = reduceNumber(dayM + yearM)      // Day + Year
        - tci_3 = reduceNumber(tci_1 + tci_2)
        - tci_4 = reduceNumber(monthM + yearM)    // Month + Year
        """
        day_m = self.reduce_number(self.dob_day)
        month_m = self.reduce_number(self.dob_month)
        year_m = self.reduce_number(self.dob_year)

        tci_1 = self.reduce_number(month_m + day_m)
        tci_2 = self.reduce_number(day_m + year_m)
        tci_3 = self.reduce_number(tci_1 + tci_2)
        tci_4 = self.reduce_number(month_m + year_m)

        return {"tci_1": tci_1, "tci_2": tci_2, "tci_3": tci_3, "tci_4": tci_4}

    def calculate_cii(self) -> int:
        """
        Calculate Cohort Influence Index.

        Formula: reduceNumber(year) (keep master number 11/22/33)
        """
        generation = sum(int(digit) for digit in str(self.dob_year))
        return self.reduce_number_with_masters(generation)

    def calculate_tai(self) -> int:
        """
        Calculate Trading Attitude Index.

        Formula: reduceNumber(sum(int(digit) for digit in str(self.dob_day + self.dob_month))) (always 1 digit)
        """
        sum_day = sum(int(digit) for digit in str(self.dob_day))
        sum_month = sum(int(digit) for digit in str(self.dob_month))
        return self.reduce_number_no_master(sum_day + sum_month)

    def calculate_bci(self) -> Dict[str, int]:
        """
        Calculate Behavioral Challenge Index.

        Formula (keep dayR, monthR, yearR like life_path - keep master number 11/22/33):
        - bci_1 = abs(dayR - monthR)
        - bci_2 = abs(dayR - yearR)
        - bci_3 = abs(bci_1 - bci_2)
        - bci_4 = abs(monthR - yearR)
        """
        bci_1 = abs(self.day_r_no_master - self.month_r_no_master)
        bci_2 = abs(self.day_r_no_master - self.year_r_no_master)
        bci_3 = abs(bci_1 - bci_2)
        bci_4 = abs(self.month_r_no_master - self.year_r_no_master)

        return {"bci_1": bci_1, "bci_2": bci_2, "bci_3": bci_3, "bci_4": bci_4}

    def calculate_ari(self) -> int:
        """
        Calculate Analytical Reasoning Index.

        Formula: reduceNumberWithMasters(day + sum(letters_of_given_name)) (keep master number 11/22/33)
        Get the given name (last part in full name), add the value of each letter + day of birth (day)
        """
        name_parts = self._split_name_parts()
        if not name_parts:
            return 0

        given_name = name_parts[-1]  # Last part (given name)
        given_name_sum = sum(
            self.ALPHABET.get(char.upper(), 0)
            for char in given_name
            if char.upper() in self.ALPHABET
        )

        return self.reduce_number_with_masters(self.dob_day + given_name_sum)

    def calculate_age_tci(self) -> List[int]:
        """
        Calculate Age Trading Cycle Index.

        Formula:
        - If life_path ∈ {11,22,33} ⇒ start = 36 - 4 = 32
        - Otherwise 36 - life_path
        - Array of 4 milestones: [start, start+9, start+18, start+27]
        """
        life_path = self.calculate_ppa()

        if life_path in self.MASTER_NUMBERS:
            start = 32  # 36 - 4
        else:
            start = 36 - life_path

        return [start, start + 9, start + 18, start + 27]

    def calculate_alignment_signals(self) -> Dict[str, int]:
        """
        Calculate Alignment Signals (AMI, MRI and DAI).

        Formula (with currentDate = dd/mm/yyyy):
        - ami = reduceNumber(day + month + currentYear)      // keep master number 11/22
        - mri = reduceNumber(currentMonth + personal_year)
        - dai = reduceNumber(currentDay + currentMonth + personal_year)
        """
        current_year = self.current_datetime.year
        current_month = self.current_datetime.month
        current_day = self.current_datetime.day

        # Annual Momentum Index (AMI)
        personal_year = self.dob_day + self.dob_month + current_year

        if current_month < self.dob_month or (
            current_month == self.dob_month and current_day < self.dob_day
        ):
            personal_year -= 1

        personal_year = self.reduce_number_no_master(personal_year)

        # Monthly Rhythm Index (MRI)
        personal_month = self.reduce_number_no_master(current_month + personal_year)

        # Daily Alignment Index (DAI)
        personal_day = self.reduce_number_no_master(
            current_day + current_month + personal_year
        )

        return {"ami": personal_year, "mri": personal_month, "dai": personal_day}

    def get_all_tbi_indicators(self) -> Dict[str, Union[int, str, List[int]]]:
        """Calculate all TBI indicators similar to numerology calculation"""
        return {
            "day_of_birth": self.dob_date.strftime("%d/%m/%Y"),
            "current_date": self.current_datetime.strftime("%d/%m/%Y"),
            "edi": self.calculate_edi(),
            "ppai": self.calculate_ppai(),
            "spi": self.calculate_spi(),
            "cmi": self.calculate_cmi(),
            "mpi": self.calculate_mpi(),
            "ri": self.calculate_ri(),
            "ioci": self.calculate_ioci(),
            "tai": self.calculate_tai(),
            "ppa": self.calculate_ppa(),
            "wmi": self.get_wmi(),
            "ssi": self.calculate_ssi(),
            "sai": self.calculate_sai(),
            "bci": self.calculate_bci(),
            "nei": self.calculate_nei(),
            "bli": self.check_bli(),
            "ari": self.calculate_ari(),
            "tci": self.calculate_tci_phase(),
            "cii": self.calculate_cii(),
            "alignment_signals": self.calculate_alignment_signals(),
            "age_tci": self.calculate_age_tci(),
        }

    def format_indicators(self, indicators_index, birthdate):
        out = [str, list, dict]

        indicators = []

        extra = ["age_tci", "tci", "bci"]

        for key, value in indicators_index.items():
            # get single number indicators
            if type(value) not in out:
                indicators = self.format(key, value, indicators)

            # get indicators in list
            elif isinstance(value, list) and key not in extra:
                for item in value:
                    indicators = self.format(key, item, indicators)

            # get indicators in dict
            elif isinstance(value, dict) and key not in extra:
                for k, v in value.items():
                    indicators = self.format(k, v, indicators)

        # Map age to indicators
        age = self.calculate_age(birthdate)

        id = self.mapping_age(age, indicators_index["age_tci"])

        age_tci = indicators_index["age_tci"][id - 1]
        tci = indicators_index["tci"][f"tci_{id}"]
        bci = indicators_index["bci"][f"bci_{id}"]

        indicators = self.format("tci", tci, indicators)

        indicators = self.format("bci", bci, indicators)

        return indicators

    def calculate_age(self, birthday, current_date=None):
        dob = datetime.strptime(birthday, "%d/%m/%Y")
        if current_date:
            current = datetime.strptime(current_date, "%d/%m/%Y")
        else:
            # Use current time in Vietnam timezone
            vntz = pytz.timezone("Asia/Ho_Chi_Minh")
            current = datetime.now(vntz)

        # Calculate current age
        age = current.year - dob.year
        if current.month < dob.month or (
            current.month == dob.month and current.day < dob.day
        ):
            age -= 1
        return age

    def mapping_age(self, age, age_tci):
        id = bisect.bisect_left(age_tci, age)
        return id + 1

    def format(self, key, value, indicators):
        out = indicators.copy()
        out.append({"category": key, "index": str(value)})
        return out

    def get_tbi_summary(self) -> Dict[str, Any]:
        """Get summary of TBI indicators"""
        indicators = self.get_all_tbi_indicators()
        indicators = self.format_indicators(indicators, self.dob)
        return indicators


class TBICalculatorFactory:
    """Factory class to create TBI Calculator"""

    @staticmethod
    def create_calculator(
        dob: str, name: str, current_date: str = None
    ) -> TBICalculator:
        """Create TBI Calculator instance"""
        return TBICalculator(dob, name, current_date)

    @staticmethod
    def create_calculator_for_today(dob: str, name: str) -> TBICalculator:
        """Calculate TBI Calculator with current date"""
        return TBICalculator(dob, name)


class TBIService:
    def __init__(self):
        pass

    def get_tbi_docs(self, indicators: List[Dict[str, str]], session_id: str) -> Dict:
        # url = "http://localhost:8111/api/v1/documents/content-by-indicators"
        temp_url = TBI_DOCS_URL

        response = requests.post(
            temp_url, json=indicators, params={"session_id": session_id}
        )
        return response.json()


def calculate_tbi(dob: str, name: str, current_date: str):
    """
    Calculate TBI indicators based on name, birthday and current date

    Args:
        dob: Birthday (dd/mm/yyyy)
        name: Full name
        current_date: Current date (dd/mm/yyyy)

    Returns:
        Dictionary of TBI indicators
    """
    calculator = TBICalculatorFactory.create_calculator(dob, name, current_date)
    return calculator.get_tbi_summary()


def retrieve_tbi_docs(
    dob: str, name: str, current_date: str, session_id: str = None
) -> Dict:
    """
    Retrieve TBI documents based on name, birthday and current date

    Args:
        dob: Birthday (dd/mm/yyyy)
        name: Full name
        current_date: Current date (dd/mm/yyyy)
        session_id: Session ID for document retrieval

    Returns:
        Dictionary of TBI documents
    """
    # Calculate TBI indicators
    indicators = calculate_tbi(dob, name, current_date)

    # Get TBI docs
    tbi = TBIService()
    docs = tbi.get_tbi_docs(indicators, session_id)

    return docs


def parse_tbi_docs(docs):
    """Parse list of docs to markdown structure"""
    result = []

    # If docs is a string (error message or plain text), return it directly
    if isinstance(docs, str):
        return docs

    # If docs is a dict, try to extract a list under a common key
    if isinstance(docs, dict):
        # common keys might be 'data', 'results', 'docs', or similar
        for key in ("data", "results", "docs", "items"):
            if key in docs and isinstance(docs[key], (list, tuple)):
                docs = docs[key]
                break
        else:
            # If it's a dict but doesn't contain a list, return a string representation
            try:
                return json.dumps(docs, ensure_ascii=False)
            except Exception:
                return str(docs)

    if not isinstance(docs, (list, tuple)):
        # Unexpected type, return safe string
        try:
            return json.dumps(docs, ensure_ascii=False)
        except Exception:
            return str(docs)

    for doc in docs:
        if not isinstance(doc, dict):
            # skip non-dict entries
            continue
        content = doc.get("content")
        if content and "Document not found" not in content:
            category = str(doc.get("category", "")).upper()
            result.append(f"## {category}")
            result.append(content)
            result.append("")  # empty line

    return "\n".join(result)


def tbi_data_wrapper(input_data):
    """Wrapper function to call retrieve_tbi_docs with correct parameters"""
    raw_data = retrieve_tbi_docs(
        dob=input_data["dob"],
        name=input_data["name"],
        current_date=input_data["current_date"],
        session_id=input_data["session_id"],
    )
    try:
        docs = parse_tbi_docs(raw_data)
    except Exception as e:
        # Return a safe message rather than raising to the caller
        docs = f"Failed to parse TBI docs: {e}"

    return docs


def get_TBI_data(
    question: str,
    dob: str,
    name: str,
    session_id: str = SESSION_DATA_TBI,
):
    """Get TBI data based on question, dob, name and session_id"""
    tbi_data = tbi_data_wrapper(
        {
            "question": question,
            "dob": dob,
            "name": name,
            "current_date": None,
            "session_id": session_id,
        }
    )
    return tbi_data


if __name__ == "__main__":
    print(get_TBI_data("TBI", "01/01/2000", "John Doe"))



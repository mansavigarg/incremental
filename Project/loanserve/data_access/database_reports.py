"""Aggregate reports computed in SQL."""

import sqlite3


class DatabaseReports:
    def __init__(self, database_path):
        self.connection = sqlite3.connect(database_path)
        self.connection.row_factory = sqlite3.Row

    def default_rate_by_product(self):
        rows = self.connection.execute("""
            SELECT loan_type, COUNT(*) AS applications, SUM(defaulted) AS defaults,
                   ROUND(1.0 * SUM(defaulted) / COUNT(*), 4) AS default_rate
            FROM loan_applications GROUP BY loan_type ORDER BY loan_type
        """)
        return [dict(row) for row in rows]

    def volume_by_year(self):
        rows = self.connection.execute("""
            SELECT SUBSTR(application_date, 1, 4) AS application_year,
                   COUNT(*) AS applications, SUM(loan_amount_inr) AS total_amount_inr
            FROM loan_applications GROUP BY application_year ORDER BY application_year
        """)
        return [dict(row) for row in rows]

    def exposure_by_city(self, minimum_applications):
        rows = self.connection.execute("""
            SELECT applicant_city, COUNT(*) AS applications,
                   SUM(loan_amount_inr) AS total_amount_inr,
                   ROUND(1.0 * SUM(defaulted) / COUNT(*), 4) AS default_rate
            FROM loan_applications GROUP BY applicant_city
            HAVING COUNT(*) >= ? ORDER BY total_amount_inr DESC
        """, (minimum_applications,))
        return [dict(row) for row in rows]


if __name__ == "__main__":
    reports = DatabaseReports("database/loanserve.db")
    print(reports.default_rate_by_product())
    print(reports.volume_by_year())
    print(reports.exposure_by_city(1250)[:1])
    reports.connection.close()

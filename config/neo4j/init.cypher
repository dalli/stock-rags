// Neo4j initialization script
// This script creates indexes and constraints for the knowledge graph

// Company indexes and constraints
CREATE CONSTRAINT company_ticker IF NOT EXISTS FOR (c:Company) REQUIRE c.ticker IS UNIQUE;
CREATE INDEX company_name IF NOT EXISTS FOR (c:Company) ON (c.name);
CREATE FULLTEXT INDEX company_search IF NOT EXISTS FOR (c:Company) ON EACH [c.name, c.aliases_text];

// Report indexes
CREATE INDEX report_id IF NOT EXISTS FOR (r:Report) ON (r.report_id);
CREATE INDEX report_date IF NOT EXISTS FOR (r:Report) ON (r.publish_date);

// Industry indexes
CREATE INDEX industry_name IF NOT EXISTS FOR (i:Industry) ON (i.name);

// Theme indexes
CREATE INDEX theme_name IF NOT EXISTS FOR (t:Theme) ON (t.name);

// Analyst indexes
CREATE INDEX analyst_name IF NOT EXISTS FOR (a:Analyst) ON (a.name);

// SecurityFirm indexes
CREATE INDEX firm_name IF NOT EXISTS FOR (s:SecurityFirm) ON (s.name);

// Sample data for testing (optional - can be removed in production)
// Create a sample company
MERGE (c:Company {ticker: "005930"})
SET c.name = "Samsung Electronics",
    c.aliases_text = "Samsung Electronics 삼성전자";

// Create a sample industry
MERGE (i:Industry {name: "Semiconductors"})
SET i.parent_industry = "Technology";

// Link company to industry
MATCH (c:Company {ticker: "005930"})
MATCH (i:Industry {name: "Semiconductors"})
MERGE (c)-[:BELONGS_TO]->(i);

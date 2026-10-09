

# AI Procurement Assistant



An AI-assisted procurement analytics application that allows users to explore California government purchasing data through natural-language questions.



The application combines a FastAPI backend, MongoDB database, Google Gemini integration, and React frontend to provide procurement summaries, rankings, interactive charts, and explanations of how queries are interpreted.



\## Project Overview



The AI Procurement Assistant makes procurement data easier to explore without requiring users to write MongoDB queries.



Users can ask questions such as:



\- How much was spent in Q2 2013?

\- How many purchase orders were created in March 2014?

\- Which department spent the most in 2014?

\- What were the top 5 suppliers in March 2014?

\- What were the most frequently purchased items in 2015?



The backend interprets supported questions, validates the resulting query plan, executes predefined MongoDB analytics, and returns structured results and readable answers.



\## Technology Stack



\### Backend

\- Python

\- FastAPI

\- MongoDB

\- PyMongo

\- Google Gemini API

\- Pydantic



\### Frontend

\- React

\- Vite

\- JavaScript

\- CSS



\## Dataset



Source: California government purchase order data, 2012â€“2015.



Original CSV filename:



`PURCHASE ORDER DATA EXTRACT 2012-2015\_0.csv`



The imported dataset contains:



\- 346,018 procurement line-item records

\- Approximately 200,526 unique nonblank purchase order numbers

\- Total recorded spending of $151,243,580,498.20



Important fields include:



\- Creation Date

\- Purchase Order Number

\- Department Name

\- Supplier Name

\- Item Name

\- Total Price



During import, the application also creates:



\- `creation\_date\_parsed`: MongoDB-compatible date

\- `total\_price\_numeric`: numeric spending value



The raw dataset is not included in the repository because of its size. Users must obtain the original CSV separately.



\## Main Features



\### Natural-Language Procurement Analytics



The application supports:



1\. Total procurement spending

2\. Procurement record counts

3\. Top suppliers by spending

4\. Top departments by spending

5\. Top items by spending

6\. Yearly spending summaries

7\. Unique purchase order counts

8\. Highest-spending quarter

9\. Most frequently recorded items



Supported queries can include filters such as year, month, quarter, department, and supplier, depending on the analysis type.



\### Dashboard



The dashboard displays procurement summary statistics, spending trends, and leading suppliers and departments.



\### Smart Suggested Questions



Users can click suggested procurement questions instead of typing them manually.



\### Interactive Charts



Supported ranking and spending results are displayed using charts alongside the textual answer.



\### Procurement Insights



The application generates factual insights based on query results, including comparisons and summary observations.



\### Explain My Query



An expandable explanation panel displays:



\- Selected analysis type

\- Interpretation source

\- Applied filters

\- Result limits where relevant

\- Calculation description



This improves transparency by helping users understand how the application interprets their questions.



\## System Architecture



```text

React Frontend

&#x20;     |

&#x20;     | HTTP requests

&#x20;     v

FastAPI Backend

&#x20;     |

&#x20;     v

Question Interpretation

(Local Parser / Gemini Fallback)

&#x20;     |

&#x20;     v

Validated Query Plan

&#x20;     |

&#x20;     v

MongoDB Query Executor

&#x20;     |

&#x20;     v

Procurement Database

&#x20;     |

&#x20;     v

Answer + Insights + Chart Data

&#x20;     |

&#x20;     v

React Frontend

```



The backend uses a controlled set of supported MongoDB operations rather than executing arbitrary database commands generated from user text.



\## Installation



\### Prerequisites



Install:



\- Python

\- Node.js and npm

\- MongoDB Community Server

\- Git



A Google Gemini API key is also required for Gemini-backed interpretation.



\### 1. Clone the Repository



```bash

git clone YOUR\_REPOSITORY\_URL

cd AI\_Procurement\_Assistant

```



Replace `YOUR\_REPOSITORY\_URL` with the actual GitHub repository URL.



\### 2. Create a Python Virtual Environment



On Windows PowerShell:



```powershell

python -m venv venv

.\\venv\\Scripts\\Activate.ps1

```



\### 3. Install Backend Dependencies



```powershell

python -m pip install -r requirements.txt

```



\### 4. Configure Environment Variables



Copy `.env.example` to `.env`:



```powershell

Copy-Item .env.example .env

```



Edit `.env` and set:



```dotenv

GEMINI\_API\_KEY=your\_actual\_api\_key

```



Never commit the actual `.env` file.



\### 5. Start MongoDB



Ensure the local MongoDB server is running at:



`mongodb://localhost:27017/`



The application uses:



\- Database: `procurement\_ai`

\- Collection: `purchase\_orders`



\### 6. Import the Dataset



Obtain the original California procurement CSV.



From the project root, run:



```powershell

python -m backend.import\_data "C:\\path\\to\\PURCHASE ORDER DATA EXTRACT 2012-2015\_0.csv"

```



The import script:



\- Preserves original CSV columns

\- Converts monetary values to numbers

\- Converts creation dates to datetime values

\- Inserts records in batches

\- Refuses to import if the target collection already contains data



The script is intended for an empty target collection. If an import is interrupted, inspect the collection before retrying.



Verify the database:



```powershell

python -m backend.database

```



\### 7. Start the Backend



From the project root:



```powershell

python -m uvicorn backend.main:app --reload

```



Backend URL:



`http://127.0.0.1:8000`



Interactive API documentation:



`http://127.0.0.1:8000/docs`



\### 8. Start the Frontend



Open another terminal:



```powershell

cd react-frontend

npm install

npm run dev

```



Open:



`http://localhost:5173`



The Vite development server proxies API requests to the backend.



\## Evaluation



The project includes an automated evaluation script:



```powershell

python -m backend.evaluate\_agent

```



Latest evaluation result:



| Metric | Result |

|---|---|

| Test cases | 18 |

| Passed | 18 |

| Failed | 0 |

| Pass rate | 100% |



The evaluation covers supported analytics, date filtering, unique purchase-order counts, spending rankings, and rejection of invalid or unsupported requests.



Report:



`evaluation\_results/expanded\_evaluation\_report.csv`



The 100% pass rate refers specifically to these 18 defined test cases.



\## Production Build



To build the React frontend:



```powershell

cd react-frontend

npm run build

```



The production build has been verified successfully.



\## Project Structure



```text

AI\_Procurement\_Assistant/

|

|-- backend/

|   |-- main.py

|   |-- database.py

|   |-- import\_data.py

|   |-- query\_engine.py

|   |-- query\_executor.py

|   |-- insights\_engine.py

|   |-- evaluate\_agent.py

|

|-- react-frontend/

|   |-- src/

|   |-- public/

|   |-- package.json

|   |-- vite.config.js

|

|-- tests/

|-- evaluation\_results/

|-- .env.example

|-- .gitignore

|-- requirements.txt

|-- README.md

```



\## Limitations



\- Natural-language support is limited to recognized procurement analysis types.

\- Gemini API availability and quotas can affect fallback interpretation.

\- The application requires a running MongoDB instance containing the prepared dataset.

\- The dataset covers the years represented in the source CSV.

\- Item frequency counts represent line-item occurrences, not purchased unit quantities.

\- Purchase order counts use distinct nonblank purchase order numbers, not the total number of line-item records.

\- The current implementation uses the Google GenAI SDK and a local question parser, not a LangChain or LangGraph agent.



\## Future Improvements



Possible enhancements include:



\- Broader natural-language query coverage

\- More advanced multi-turn query interpretation

\- Additional comparisons and visualizations

\- Dataset upload and management

\- User authentication and role-based access

\- Deployment to a cloud environment



\## Demonstration



A demonstration video will be added to the repository submission.



\## Security



\- API keys are stored in `.env`.

\- `.env` is excluded from version control.

\- `.env.example` contains only a placeholder.

\- Arbitrary database commands are not accepted through the supported analytics interface.




